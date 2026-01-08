import { useState, useEffect } from 'react'
import { X, Settings as SettingsIcon, Server, Key, Check } from 'lucide-react'
import { MCPConfig } from './MCPConfig'
import { ProviderConfig } from './ProviderConfig'

export interface MCPServerConfig {
  name: string
  command: string
  args: string[]
  env: Record<string, string>
  enabled: boolean
}

export interface ProviderSettings {
  id: string
  name: string
  type: 'anthropic' | 'openai'
  apiKey: string
  baseUrl?: string
  model: string
  isDefault: boolean
}

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

type TabType = 'providers' | 'mcp'

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('providers')
  const [providers, setProviders] = useState<ProviderSettings[]>([])
  const [mcpServers, setMcpServers] = useState<MCPServerConfig[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  // Load settings on mount
  useEffect(() => {
    if (isOpen) {
      loadSettings()
    }
  }, [isOpen])

  const loadSettings = async () => {
    try {
      // Try to load from backend API first
      const [providersRes, mcpRes] = await Promise.all([
        fetch('/api/config/providers').catch(() => null),
        fetch('/api/config/mcp').catch(() => null),
      ])

      // Load providers from API or localStorage fallback
      if (providersRes?.ok) {
        const data = await providersRes.json()
        if (data.providers && data.providers.length > 0) {
          setProviders(data.providers.map((p: Record<string, unknown>) => ({
            id: p.id as string,
            name: p.name as string,
            type: p.type as 'anthropic' | 'openai',
            apiKey: p.api_key_env ? '' : '', // Don't expose actual keys
            apiKeyEnv: p.api_key_env as string | undefined, // Show env var reference
            apiKeySet: p.api_key_set as boolean,
            baseUrl: p.base_url as string | undefined,
            model: p.model as string,
            isDefault: p.is_default as boolean,
          })))
        } else {
          // Default provider
          setProviders([{
            id: 'default',
            name: 'Anthropic (Default)',
            type: 'anthropic',
            apiKey: '',
            model: 'claude-sonnet-4-20250514',
            isDefault: true,
          }])
        }
      } else {
        // Fallback to localStorage
        const savedProviders = localStorage.getItem('honolulu_providers')
        if (savedProviders) {
          setProviders(JSON.parse(savedProviders))
        } else {
          setProviders([{
            id: 'default',
            name: 'Anthropic (Default)',
            type: 'anthropic',
            apiKey: '',
            model: 'claude-sonnet-4-20250514',
            isDefault: true,
          }])
        }
      }

      // Load MCP servers from API or localStorage fallback
      if (mcpRes?.ok) {
        const data = await mcpRes.json()
        if (data.servers) {
          setMcpServers(data.servers.map((s: Record<string, unknown>) => ({
            name: s.name as string,
            command: s.command as string,
            args: s.args as string[],
            env: s.env as Record<string, string>,
            enabled: s.enabled as boolean,
          })))
        }
      } else {
        const savedMcp = localStorage.getItem('honolulu_mcp_servers')
        if (savedMcp) {
          setMcpServers(JSON.parse(savedMcp))
        }
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
    }
  }

  const saveSettings = async () => {
    setIsSaving(true)
    setSaveMessage(null)

    try {
      // Save to localStorage as backup
      localStorage.setItem('honolulu_providers', JSON.stringify(providers))
      localStorage.setItem('honolulu_mcp_servers', JSON.stringify(mcpServers))

      // Call backend API to update config file
      const response = await fetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          providers: providers.map(p => ({
            id: p.id,
            name: p.name,
            type: p.type,
            api_key: p.apiKey,
            base_url: p.baseUrl || null,
            model: p.model,
            is_default: p.isDefault,
          })),
          mcp_servers: mcpServers.map(s => ({
            name: s.name,
            command: s.command,
            args: s.args,
            env: s.env,
            enabled: s.enabled,
          })),
        }),
      })

      if (response.ok) {
        const result = await response.json()
        // Show detailed message based on hot reload status
        let message = result.message || 'Settings saved!'
        if (result.hot_reload?.success) {
          message = 'Settings saved and applied!'
        }
        if (result.warnings?.length > 0) {
          message += ` (${result.warnings.join(', ')})`
        }
        setSaveMessage(message)
      } else {
        const error = await response.json()
        setSaveMessage(`Failed to save: ${error.detail || 'Unknown error'}`)
      }

      setTimeout(() => setSaveMessage(null), 8000)
    } catch (error) {
      console.error('Failed to save settings:', error)
      setSaveMessage('Failed to save settings. Check console for details.')
    } finally {
      setIsSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-surface border border-border rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <SettingsIcon size={20} className="text-primary" />
            <h2 className="text-lg font-semibold text-text">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-surface-light rounded text-text-muted hover:text-text"
          >
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setActiveTab('providers')}
            className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'providers'
                ? 'text-primary border-b-2 border-primary'
                : 'text-text-muted hover:text-text'
            }`}
          >
            <Key size={16} />
            Model Providers
          </button>
          <button
            onClick={() => setActiveTab('mcp')}
            className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'mcp'
                ? 'text-primary border-b-2 border-primary'
                : 'text-text-muted hover:text-text'
            }`}
          >
            <Server size={16} />
            MCP Servers
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'providers' && (
            <ProviderConfig
              providers={providers}
              onChange={setProviders}
            />
          )}
          {activeTab === 'mcp' && (
            <MCPConfig
              servers={mcpServers}
              onChange={setMcpServers}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-surface-light">
          <div className="text-sm text-text-muted">
            {saveMessage && (
              <span className={saveMessage.includes('Failed') ? 'text-error' : 'text-success'}>
                {saveMessage}
              </span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-text-muted hover:text-text transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={saveSettings}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-dark text-white text-sm rounded-lg transition-colors disabled:opacity-50"
            >
              {isSaving ? (
                'Saving...'
              ) : (
                <>
                  <Check size={16} />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export { MCPConfig } from './MCPConfig'
export { ProviderConfig } from './ProviderConfig'
