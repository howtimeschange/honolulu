import { Wifi, WifiOff, Circle, PanelRightOpen, PanelRightClose } from 'lucide-react'

interface StatusBarProps {
  isConnected: boolean
  hasSession: boolean
  model?: {
    provider: string
    name: string
  }
  onToggleWorkPanel: () => void
  isWorkPanelOpen: boolean
}

export function StatusBar({ isConnected, hasSession, model, onToggleWorkPanel, isWorkPanelOpen }: StatusBarProps) {
  return (
    <footer className="h-8 border-t border-border flex items-center justify-between px-4 text-xs text-text-muted bg-surface">
      <div className="flex items-center gap-4">
        {/* Connection Status */}
        <div className="flex items-center gap-1.5">
          {isConnected ? (
            <>
              <Wifi size={14} className="text-success" />
              <span>Connected</span>
            </>
          ) : hasSession ? (
            <>
              <WifiOff size={14} className="text-error" />
              <span>Disconnected</span>
            </>
          ) : (
            <>
              <Circle size={14} className="text-accent" />
              <span>Ready</span>
            </>
          )}
        </div>

        {/* Model Info */}
        {model && (
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">Model:</span>
            <span className="text-text">{model.name}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Toggle Work Panel */}
        <button
          onClick={onToggleWorkPanel}
          className="p-1 hover:bg-surface-light rounded transition-colors"
          title={isWorkPanelOpen ? 'Hide Work Panel' : 'Show Work Panel'}
        >
          {isWorkPanelOpen ? (
            <PanelRightClose size={16} />
          ) : (
            <PanelRightOpen size={16} />
          )}
        </button>
      </div>
    </footer>
  )
}
