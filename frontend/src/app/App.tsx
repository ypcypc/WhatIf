import { useCallback, useState } from 'react'

import { GameplayPage } from '@/pages/gameplay-page'
import { StartPage } from '@/pages/start-page'

export default function App() {
  const [page, setPage] = useState<'start' | 'gameplay'>('start')
  const [fading, setFading] = useState(false)

  const navigateTo = useCallback((target: 'start' | 'gameplay') => {
    setFading(true)
    setTimeout(() => {
      setPage(target)
      setFading(false)
    }, 300)
  }, [])

  return (
    <div className={`page-transition ${fading ? 'page-fade-out' : ''}`}>
      {page === 'gameplay'
        ? <GameplayPage />
        : (
            <StartPage
              onStartGame={() => navigateTo('gameplay')}
              onLoadSave={() => navigateTo('gameplay')}
            />
          )
      }
    </div>
  )
}
