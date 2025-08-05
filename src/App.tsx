import { useState } from 'react'
import { GlassMainMenu } from './components/GlassMainMenu'
import { GlassGameScreen } from './components/GlassGameScreen'
import AnchorServiceTest from './components/AnchorServiceTest'
import AnchorContextDemo from './components/AnchorContextDemo'
import { GlassCard } from './components/ui/GlassCard'
import { GlassButton } from './components/ui/GlassButton'
import { X } from 'lucide-react'

type AppScreen = 'menu' | 'game' | 'interactive' | 'anchor-demo' | 'api-test'

function App() {
  const [currentScreen, setCurrentScreen] = useState<AppScreen>('menu')

  const renderCurrentScreen = () => {
    switch (currentScreen) {
      case 'menu':
        return (
          <GlassMainMenu
            onStartGame={() => setCurrentScreen('game')}
            onStartInteractive={() => setCurrentScreen('interactive')}
            onShowAnchorDemo={() => setCurrentScreen('anchor-demo')}
            onShowAnchorTest={() => setCurrentScreen('api-test')}
          />
        )
      
      case 'game':
      case 'interactive':
        return (
          <GlassGameScreen
            onBack={() => setCurrentScreen('menu')}
          />
        )
      
      case 'anchor-demo':
        return (
          <div className="fixed inset-0 bg-black">
            {/* Fullscreen Background */}
            <div className="absolute inset-0">
              <img 
                src="/bg.jpg" 
                alt="Demo Background" 
                className="absolute inset-0 w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-black/40" />
            </div>
            
            <div className="absolute top-6 left-6 z-50">
              <GlassButton
                variant="secondary"
                onClick={() => setCurrentScreen('menu')}
              >
                <X size={16} />
                返回主菜单
              </GlassButton>
            </div>
            
            <div className="absolute inset-0 flex items-center justify-center p-6">
              <GlassCard 
                blur="xl" 
                opacity="high" 
                className="w-full max-w-4xl max-h-[80vh] overflow-auto"
                animate={true}
              >
                <div className="p-6">
                  <h2 className="text-xl font-bold text-white mb-4">锚点上下文演示</h2>
                  <AnchorContextDemo onBack={() => setCurrentScreen('menu')} />
                </div>
              </GlassCard>
            </div>
          </div>
        )
      
      case 'api-test':
        return (
          <div className="fixed inset-0 bg-black">
            {/* Fullscreen Background */}
            <div className="absolute inset-0">
              <img 
                src="/bg.jpg" 
                alt="Test Background" 
                className="absolute inset-0 w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-black/40" />
            </div>
            
            <div className="absolute top-6 left-6 z-50">
              <GlassButton
                variant="secondary"
                onClick={() => setCurrentScreen('menu')}
              >
                <X size={16} />
                返回主菜单
              </GlassButton>
            </div>
            
            <div className="absolute inset-0 flex items-center justify-center p-6">
              <GlassCard 
                blur="xl" 
                opacity="high" 
                className="w-full max-w-4xl max-h-[80vh] overflow-auto"
                animate={true}
              >
                <div className="p-6">
                  <h2 className="text-xl font-bold text-white mb-4">API 连通性测试</h2>
                  <AnchorServiceTest />
                </div>
              </GlassCard>
            </div>
          </div>
        )
      
      default:
        return null
    }
  }

  return (
    <div className="app-container">
      {renderCurrentScreen()}
    </div>
  )
}

export default App
