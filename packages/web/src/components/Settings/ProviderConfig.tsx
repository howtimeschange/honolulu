import { useState } from 'react'
import { Plus, Trash2, ChevronDown, ChevronUp, Eye, EyeOff } from 'lucide-react'
import type { ProviderSettings } from './index'

interface ProviderConfigProps {
  providers: ProviderSettings[]
  onChange: (providers: ProviderSettings[]) => void
}

const MODEL_OPTIONS = {
  anthropic: [
    'claude-opus-4-20250514',
    'claude-sonnet-4-20250514',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-haiku-20241022',
  ],
  openai: [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4-turbo',
    'gpt-3.5-turbo',
  ],
}

export function ProviderConfig({ providers, onChange }: ProviderConfigProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [showApiKey, setShowApiKey] = useState<Record<string, boolean>>({})

  const addProvider = () => {
    const newProvider: ProviderSettings = {
      id: crypto.randomUUID(),
      name: `Provider ${providers.length + 1}`,
      type: 'anthropic',
      apiKey: '',
      model: 'claude-sonnet-4-20250514',
      isDefault: providers.length === 0,
    }
    onChange([...providers, newProvider])
    setExpandedId(newProvider.id)
  }

  const updateProvider = (id: string, updates: Partial<ProviderSettings>) => {
    onChange(providers.map(p => p.id === id ? { ...p, ...updates } : p))
  }

  const removeProvider = (id: string) => {
    const remaining = providers.filter(p => p.id !== id)
    // If removed provider was default, make first one default
    if (remaining.length > 0 && !remaining.some(p => p.isDefault)) {
      remaining[0].isDefault = true
    }
    onChange(remaining)
  }

  const setAsDefault = (id: string) => {
    onChange(providers.map(p => ({ ...p, isDefault: p.id === id })))
  }

  const toggleApiKeyVisibility = (id: string) => {
    setShowApiKey(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-text">Model Providers</h3>
          <p className="text-xs text-text-muted mt-1">
            Configure AI model providers and API keys
          </p>
        </div>
        <button
          onClick={addProvider}
          className="flex items-center gap-1 px-3 py-1.5 text-sm bg-primary hover:bg-primary-dark text-white rounded-lg transition-colors"
        >
          <Plus size={16} />
          Add Provider
        </button>
      </div>

      {providers.length === 0 ? (
        <div className="text-center py-8 text-text-muted">
          <p>No providers configured</p>
          <p className="text-xs mt-1">Add a provider to get started</p>
        </div>
      ) : (
        <div className="space-y-2">
          {providers.map((provider) => (
            <div
              key={provider.id}
              className="border border-border rounded-lg overflow-hidden"
            >
              {/* Header */}
              <div
                className="flex items-center justify-between px-4 py-3 bg-surface-light cursor-pointer"
                onClick={() => setExpandedId(expandedId === provider.id ? null : provider.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-text">{provider.name}</span>
                  {provider.isDefault && (
                    <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                      Default
                    </span>
                  )}
                  <span className="text-xs text-text-muted">
                    {provider.type} / {provider.model}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {!provider.isDefault && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setAsDefault(provider.id)
                      }}
                      className="px-2 py-1 text-xs text-text-muted hover:text-primary transition-colors"
                    >
                      Set Default
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      removeProvider(provider.id)
                    }}
                    className="p-1 text-text-muted hover:text-error transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                  {expandedId === provider.id ? (
                    <ChevronUp size={16} className="text-text-muted" />
                  ) : (
                    <ChevronDown size={16} className="text-text-muted" />
                  )}
                </div>
              </div>

              {/* Expanded Content */}
              {expandedId === provider.id && (
                <div className="p-4 space-y-4 border-t border-border">
                  {/* Name */}
                  <div>
                    <label className="block text-xs text-text-muted mb-1">Name</label>
                    <input
                      type="text"
                      value={provider.name}
                      onChange={(e) => updateProvider(provider.id, { name: e.target.value })}
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary"
                    />
                  </div>

                  {/* Type */}
                  <div>
                    <label className="block text-xs text-text-muted mb-1">Provider Type</label>
                    <select
                      value={provider.type}
                      onChange={(e) => {
                        const newType = e.target.value as 'anthropic' | 'openai'
                        updateProvider(provider.id, {
                          type: newType,
                          model: MODEL_OPTIONS[newType][0],
                        })
                      }}
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary"
                    >
                      <option value="anthropic">Anthropic (Claude)</option>
                      <option value="openai">OpenAI Compatible</option>
                    </select>
                  </div>

                  {/* API Key */}
                  <div>
                    <label className="block text-xs text-text-muted mb-1">API Key</label>
                    <div className="relative">
                      <input
                        type={showApiKey[provider.id] ? 'text' : 'password'}
                        value={provider.apiKey}
                        onChange={(e) => updateProvider(provider.id, { apiKey: e.target.value })}
                        placeholder={provider.type === 'anthropic' ? 'sk-ant-...' : 'sk-...'}
                        className="w-full px-3 py-2 pr-10 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary"
                      />
                      <button
                        type="button"
                        onClick={() => toggleApiKeyVisibility(provider.id)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-text"
                      >
                        {showApiKey[provider.id] ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* Base URL (for OpenAI compatible) */}
                  <div>
                    <label className="block text-xs text-text-muted mb-1">
                      Base URL {provider.type === 'anthropic' && '(Optional)'}
                    </label>
                    <input
                      type="text"
                      value={provider.baseUrl || ''}
                      onChange={(e) => updateProvider(provider.id, { baseUrl: e.target.value || undefined })}
                      placeholder={provider.type === 'anthropic' ? 'https://api.anthropic.com' : 'https://api.openai.com/v1'}
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary"
                    />
                    <p className="text-xs text-text-muted mt-1">
                      Leave empty for default. Use custom URL for proxies or compatible APIs.
                    </p>
                  </div>

                  {/* Model */}
                  <div>
                    <label className="block text-xs text-text-muted mb-1">Model</label>
                    <select
                      value={provider.model}
                      onChange={(e) => updateProvider(provider.id, { model: e.target.value })}
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary"
                    >
                      {MODEL_OPTIONS[provider.type].map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
