import { useState, useEffect } from 'react'
import { ArrowLeft, Eye, EyeOff, Check, Loader2, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'motion/react'
import {
  getApiKeys, setApiKeys as storeApiKeys,
  getLlmConfig, setLlmConfig as storeLlmConfig,
  getLocale, setLocale as storeLocale,
  type LlmSlotConfig, type LlmConfigMap,
} from '@/lib/config-store'
import {
  updateApiKeys, testApiKey,
  getLlmConfig as fetchLlmConfig, updateLlmConfig,
} from '@/lib/api'
import i18n from '@/lib/i18n'

const PROVIDERS = ['dashscope', 'anthropic', 'gemini', 'openai', 'volcengine'] as const

type Tab = 'apiKeys' | 'modelConfig' | 'language'
const TABS: Tab[] = ['apiKeys', 'modelConfig', 'language']

interface Props {
  onBack: () => void
}

export function SettingsPage({ onBack }: Props) {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Tab>('apiKeys')

  return (
    <div className="flex h-full flex-col" style={{ zIndex: 10, position: 'relative' }}>
      {/* Header */}
      <div className="screen-hdr">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={13} />
          {t('settings.back')}
        </button>
        <span className="text-lg font-medium font-sans" style={{ color: 'var(--color-text-0)' }}>
          {t('settings.title')}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-10" style={{ borderBottom: '0.5px solid var(--color-border)' }}>
        {TABS.map(key => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`settings-tab cursor-pointer ${tab === key ? 'active' : ''}`}
          >
            {t(`settings.${key}`)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-10 py-8">
        <div className="mx-auto max-w-[720px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              {tab === 'apiKeys' && <ApiKeysTab />}
              {tab === 'modelConfig' && <ModelConfigTab />}
              {tab === 'language' && <LanguageTab />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

// --- API Keys Tab ---

function ApiKeysTab() {
  const { t } = useTranslation()
  const [keys, setKeys] = useState<Record<string, string>>({})
  const [visible, setVisible] = useState<Record<string, boolean>>({})
  const [testing, setTesting] = useState<Record<string, boolean>>({})
  const [testResult, setTestResult] = useState<Record<string, 'ok' | 'fail' | null>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getApiKeys().then(setKeys)
  }, [])

  async function handleSave() {
    await storeApiKeys(keys)
    try { await updateApiKeys(keys) } catch { /* offline */ }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  async function handleTest(provider: string) {
    const key = keys[provider]
    if (!key) return
    setTesting(p => ({ ...p, [provider]: true }))
    setTestResult(p => ({ ...p, [provider]: null }))
    try {
      await testApiKey(provider, key)
      setTestResult(p => ({ ...p, [provider]: 'ok' }))
    } catch {
      setTestResult(p => ({ ...p, [provider]: 'fail' }))
    }
    setTesting(p => ({ ...p, [provider]: false }))
  }

  return (
    <div className="space-y-3">
      {PROVIDERS.map(provider => (
        <div key={provider} className="api-card">
          <div className="mb-3 flex items-center justify-between">
            <label className="text-[13px] font-medium font-sans capitalize" style={{ color: 'var(--color-text-0)', letterSpacing: '0.04em' }}>
              {provider}
            </label>
            {testResult[provider] === 'ok' && (
              <span className="flex items-center gap-1 text-xs" style={{ color: '#80e8a0' }}>
                <Check size={12} /> {t('settings.testSuccess')}
              </span>
            )}
            {testResult[provider] === 'fail' && (
              <span className="flex items-center gap-1 text-xs text-red-400">
                <X size={12} /> {t('settings.testFailed')}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type={visible[provider] ? 'text' : 'password'}
                value={keys[provider] ?? ''}
                onChange={e => setKeys(p => ({ ...p, [provider]: e.target.value }))}
                placeholder={t('settings.apiKeyPlaceholder')}
                className="api-input w-full pr-10"
              />
              <button
                onClick={() => setVisible(p => ({ ...p, [provider]: !p[provider] }))}
                className="icon-btn absolute right-1 top-1/2 -translate-y-1/2"
                style={{ width: 30, height: 30, border: 'none' }}
              >
                {visible[provider] ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <button
              onClick={() => handleTest(provider)}
              disabled={!keys[provider] || testing[provider]}
              className="test-btn disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {testing[provider] ? <Loader2 size={14} className="animate-spin" /> : t('settings.testConnection')}
            </button>
          </div>
        </div>
      ))}

      <button
        onClick={handleSave}
        className="save-btn"
      >
        {saved ? t('settings.saved') : t('settings.save')}
      </button>
    </div>
  )
}

// --- Model Config Tab ---

function ModelConfigTab() {
  const { t } = useTranslation()
  const [config, setConfig] = useState<LlmConfigMap | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getLlmConfig().then(local => {
      if (local) {
        setConfig(local)
      } else {
        fetchLlmConfig().then(setConfig).catch(() => {})
      }
    })
  }, [])

  function updateSlot(section: 'extractors' | 'agents', name: string, field: keyof LlmSlotConfig, value: string | number) {
    if (!config) return
    setConfig({
      ...config,
      [section]: {
        ...config[section],
        [name]: { ...config[section][name], [field]: value },
      },
    })
  }

  function applyPreset(model: string) {
    if (!config) return
    const updated = { ...config }
    for (const section of ['extractors', 'agents'] as const) {
      const slots = { ...updated[section] }
      for (const name of Object.keys(slots)) {
        slots[name] = { ...slots[name], model }
      }
      updated[section] = slots
    }
    setConfig(updated)
  }

  async function handleSave() {
    if (!config) return
    await storeLlmConfig(config)
    try { await updateLlmConfig(config) } catch { /* offline */ }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (!config) {
    return <p className="text-sm font-sans" style={{ color: 'var(--color-text-1)' }}>{t('app.loading')}</p>
  }

  return (
    <div className="space-y-6">
      {/* Presets */}
      <div className="flex gap-2">
        <button
          onClick={() => applyPreset('dashscope/qwen3.5-flash')}
          className="test-btn"
        >
          {t('settings.presetFlash')}
        </button>
        <button
          onClick={() => applyPreset('dashscope/qwen3.5-plus')}
          className="test-btn"
        >
          {t('settings.presetPlus')}
        </button>
      </div>

      {(['extractors', 'agents'] as const).map(section => (
        <div key={section}>
          <h3 className="mb-3 text-sm font-medium font-sans uppercase tracking-wider" style={{ color: 'var(--color-accent-gold)' }}>
            {t(`settings.${section}`)}
          </h3>
          <div className="space-y-2">
            {Object.entries(config[section]).map(([name, slot]) => (
              <div key={name} className="api-card space-y-2" style={{ padding: '12px 16px' }}>
                <span className="text-xs font-sans block" style={{ color: 'var(--color-text-1)' }} title={name}>
                  {t(`slots.${name}`, name)}
                </span>
                <input
                  value={slot.model}
                  onChange={e => updateSlot(section, name, 'model', e.target.value)}
                  className="api-input w-full"
                  style={{ padding: '6px 10px', fontSize: '12px' }}
                />
                <div className="flex gap-3">
                  <div className="flex-1">
                    <span className="text-[10px] block mb-0.5" style={{ color: 'var(--color-text-2)' }}>{t('settings.temperature')}</span>
                    <input
                      type="number" step={0.1} min={0} max={2}
                      value={slot.temperature}
                      onChange={e => updateSlot(section, name, 'temperature', parseFloat(e.target.value) || 0)}
                      className="api-input w-full"
                      style={{ padding: '6px 10px', fontSize: '12px' }}
                    />
                  </div>
                  <div className="flex-1">
                    <span className="text-[10px] block mb-0.5" style={{ color: 'var(--color-text-2)' }}>{t('settings.thinkingBudget')}</span>
                    <input
                      type="number" step={64} min={0}
                      value={slot.thinking_budget}
                      onChange={e => updateSlot(section, name, 'thinking_budget', parseInt(e.target.value) || 0)}
                      className="api-input w-full"
                      style={{ padding: '6px 10px', fontSize: '12px' }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <button onClick={handleSave} className="save-btn">
        {saved ? t('settings.saved') : t('settings.save')}
      </button>
    </div>
  )
}

// --- Language Tab ---

function LanguageTab() {
  const [locale, setLocaleState] = useState('zh-CN')

  useEffect(() => {
    getLocale().then(setLocaleState)
  }, [])

  async function handleChange(lng: string) {
    setLocaleState(lng)
    await storeLocale(lng)
    i18n.changeLanguage(lng)
  }

  const languages = [
    { code: 'zh-CN', label: '中文' },
    { code: 'en', label: 'English' },
  ]

  return (
    <div className="space-y-2">
      {languages.map(lang => (
        <button
          key={lang.code}
          onClick={() => handleChange(lang.code)}
          className="api-card w-full flex items-center justify-between cursor-pointer text-left transition-colors duration-200 font-sans"
          style={{
            borderColor: locale === lang.code ? 'var(--color-amber-border)' : undefined,
            color: locale === lang.code ? 'var(--color-text-0)' : 'var(--color-text-1)',
          }}
        >
          <span>{lang.label}</span>
          {locale === lang.code && <Check size={16} style={{ color: 'var(--color-accent-gold)' }} />}
        </button>
      ))}
    </div>
  )
}
