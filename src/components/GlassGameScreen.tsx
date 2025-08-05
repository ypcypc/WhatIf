import { type FC, useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft, 
  Play, 
  Pause, 
  SkipForward, 
  FastForward, 
  Settings,
  Volume2,
  BookOpen,
  X
} from 'lucide-react'
import InteractiveGameReader from './InteractiveGameReader'

interface GlassGameScreenProps {
  onBack: () => void
}

export const GlassGameScreen: FC<GlassGameScreenProps> = ({ onBack }) => {
  const [isPlaying, setIsPlaying] = useState(true)
  const [showBacklog, setShowBacklog] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [volume, setVolume] = useState(true)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-hide cursor during idle
  const [showCursor, setShowCursor] = useState(true)
  useEffect(() => {
    let timeout: number
    const resetTimer = () => {
      setShowCursor(true)
      clearTimeout(timeout)
      timeout = setTimeout(() => setShowCursor(false), 3000)
    }
    
    window.addEventListener('mousemove', resetTimer)
    resetTimer()
    
    return () => {
      window.removeEventListener('mousemove', resetTimer)
      clearTimeout(timeout)
    }
  }, [])

  return (
    <div className={`fixed inset-0 bg-black ${showCursor ? 'cursor-auto' : 'cursor-none'}`} ref={containerRef}>
      {/* Fullscreen Background */}
      <div className="absolute inset-0">
        <img 
          src="/bg.jpg" 
          alt="Game Background" 
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/40" />
      </div>

      {/* Top Glass Toolbar */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="fixed top-6 left-1/2 transform -translate-x-1/2 z-50"
      >
        <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-xl">
          <div className="flex items-center gap-2 px-2 py-1.5">
            <button 
              onClick={onBack}
              title="返回主菜单"
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
            >
              <ArrowLeft size={16} />
            </button>
            
            <div className="w-px h-6 bg-white/20" />
            
            <button 
              onClick={() => setIsPlaying(!isPlaying)}
              title={isPlaying ? "暂停" : "播放"}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
            >
              {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            </button>
            
            <button 
              title="快进"
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
            >
              <FastForward size={16} />
            </button>
            
            <button 
              title="跳过"
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
            >
              <SkipForward size={16} />
            </button>
            
            <div className="w-px h-6 bg-white/20" />
            
            <button 
              onClick={() => setShowBacklog(!showBacklog)}
              title="对话历史"
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
            >
              <BookOpen size={16} />
            </button>
            
            <button 
              onClick={() => setVolume(!volume)}
              title="音量"
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
            >
              <Volume2 size={16} />
            </button>
            
            <button 
              onClick={() => setShowSettings(!showSettings)}
              title="设置"
              className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
            >
              <Settings size={16} />
            </button>
          </div>
        </div>
      </motion.div>

      {/* Character Sprite Area */}
      <motion.div
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.5, type: 'spring', stiffness: 200 }}
        className="absolute bottom-0 right-8 h-[80%] max-h-[700px] pointer-events-none z-30"
      >
        <img
          src="/hero.png"
          alt="Character"
          className="h-full object-contain drop-shadow-2xl"
        />
      </motion.div>

      {/* Interactive Game Reader Component */}
      <InteractiveGameReader onBack={onBack} />

      {/* Backlog Panel */}
      {showBacklog && (
        <motion.div
          initial={{ opacity: 0, x: 400 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 400 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="absolute top-0 right-0 bottom-0 w-96 z-60"
        >
          <div className="h-full flex flex-col bg-black/60 backdrop-blur-xl border-l border-white/20 rounded-l-2xl">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <BookOpen size={20} className="text-white" />
                <h3 className="text-lg font-medium text-white">对话历史</h3>
              </div>
              <button 
                onClick={() => setShowBacklog(false)}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {/* Backlog content will be populated by game logic */}
              <div className="text-white/60 text-center py-8">
                对话历史将在这里显示
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Settings Panel */}
      {showSettings && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="absolute inset-0 flex items-center justify-center z-70"
        >
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="w-96 max-w-[90vw] p-6 bg-black/60 backdrop-blur-xl border border-white/20 rounded-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-medium text-white">设置</h3>
              <button 
                onClick={() => setShowSettings(false)}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors text-white/80 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="space-y-4 text-white/80">
              <div className="text-center py-8">
                设置选项将在这里显示
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}