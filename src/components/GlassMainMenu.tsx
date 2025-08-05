import { type FC } from 'react'
import { motion } from 'framer-motion'
import { Play, Save, Settings, TestTube, X } from 'lucide-react'
import { AdvancedGlass } from './ui/AdvancedGlass'

interface GlassMainMenuProps {
  onStartGame: () => void
  onStartInteractive: () => void
  onShowAnchorDemo: () => void
  onShowAnchorTest: () => void
  onExit?: () => void
}

const menuItems = [
  { 
    icon: Play, 
    label: 'AI 交互式故事', 
    action: 'interactive',
    description: '与 AI 一起创造独特的故事体验'
  },
  { 
    icon: Save, 
    label: '锚点上下文演示', 
    action: 'anchor-demo',
    description: '查看锚点系统的工作原理'
  },
  { 
    icon: TestTube, 
    label: 'API 连通性测试', 
    action: 'api-test',
    description: '测试与后端服务的连接状态'
  },
  { 
    icon: Settings, 
    label: '设置', 
    action: 'settings',
    description: '调整游戏设置和偏好'
  }
]

export const GlassMainMenu: FC<GlassMainMenuProps> = ({
  onStartGame,
  onStartInteractive,
  onShowAnchorDemo,
  onShowAnchorTest,
  onExit
}) => {
  const handleAction = (action: string) => {
    switch (action) {
      case 'game':
        onStartGame()
        break
      case 'interactive':
        onStartInteractive()
        break
      case 'anchor-demo':
        onShowAnchorDemo()
        break
      case 'api-test':
        onShowAnchorTest()
        break
      case 'settings':
        // TODO: Implement settings
        break
      default:
        break
    }
  }

  return (
    <div className="fixed inset-0 bg-black">
      {/* Fullscreen Background */}
      <div className="absolute inset-0">
        <img 
          src="/bg.jpg" 
          alt="Game Background" 
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/20 to-black/50" />
      </div>

      {/* Floating Particles Effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-white/20 rounded-full"
            initial={{ 
              x: Math.random() * window.innerWidth,
              y: window.innerHeight + 10
            }}
            animate={{
              y: -10,
              x: Math.random() * window.innerWidth
            }}
            transition={{
              duration: Math.random() * 20 + 20,
              repeat: Infinity,
              delay: Math.random() * 20
            }}
          />
        ))}
      </div>

      {/* Main Menu Card */}
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ 
            type: 'spring', 
            stiffness: 200, 
            damping: 25,
            delay: 0.2
          }}
        >
        <AdvancedGlass
          blur="xl"
          opacity="high"
          shadow={true}
          animate={false}
          className="w-96 p-8"
          enableTilt={true}
          enableHighlight={true}
          enableDisplacement={false}
        >
              {/* Title */}
              <motion.div 
                className="text-center mb-8"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <h1 className="text-3xl font-bold text-white mb-2">
                  AI Galgame
                </h1>
                <p className="text-white/70 text-sm">
                  智能交互式视觉小说体验
                </p>
              </motion.div>

              {/* Menu Items */}
              <div className="space-y-3">
              {menuItems.map((item, index) => (
                <motion.div
                  key={item.action}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                >
                  <button
                    className="w-full h-auto min-h-[60px] bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl px-4 py-3 transition-all duration-200 backdrop-blur-sm"
                    onClick={() => handleAction(item.action)}
                  >
                    <div className="flex items-center gap-3 text-left w-full">
                      <item.icon size={20} className="shrink-0 text-white" />
                      <div className="flex-1">
                        <div className="font-medium text-white group-hover:text-white/90">
                          {item.label}
                        </div>
                        <div className="text-xs text-white/60 mt-1">
                          {item.description}
                        </div>
                      </div>
                    </div>
                  </button>
                </motion.div>
              ))}
              </div>

              {/* Exit Button */}
              {onExit && (
                <motion.div
                  className="mt-6 pt-6 border-t border-white/10"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.9 }}
                >
                  <button
                    className="w-full bg-transparent hover:bg-white/10 border border-transparent rounded-xl px-4 py-3 transition-all duration-200 text-white/80 hover:text-white flex items-center justify-center gap-2"
                    onClick={onExit}
                  >
                    <X size={16} />
                    退出游戏
                  </button>
                </motion.div>
              )}
        </AdvancedGlass>
        </motion.div>
      </div>

      {/* Version Info */}
      <motion.div
        className="absolute bottom-4 left-4 text-white/40 text-xs"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
      >
        <p>Version 1.0.0 Beta</p>
        <p>Built with React + Framer Motion</p>
      </motion.div>
    </div>
  )
}