import { useState } from 'react'
import { Plus, Trash2, ChevronDown, ChevronUp, Play, Square, AlertCircle } from 'lucide-react'
import type { MCPServerConfig } from './index'

interface MCPConfigProps {
  servers: MCPServerConfig[]
  onChange: (servers: MCPServerConfig[]) => void
}

interface MCPTemplate {
  name: string
  command: string
  args: string[]
  env?: Record<string, string>
  description: string
}

const MCP_TEMPLATES: MCPTemplate[] = [
  {
    name: 'Filesystem',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-filesystem', '/path/to/directory'],
    description: 'Access local filesystem',
  },
  {
    name: 'GitHub',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-github'],
    env: { GITHUB_PERSONAL_ACCESS_TOKEN: '' },
    description: 'Interact with GitHub repositories',
  },
  {
    name: 'Postgres',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-postgres', 'postgresql://user:pass@localhost/db'],
    description: 'Query PostgreSQL databases',
  },
  {
    name: 'Brave Search',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-brave-search'],
    env: { BRAVE_API_KEY: '' },
    description: 'Web search with Brave',
  },
]

export function MCPConfig({ servers, onChange }: MCPConfigProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [showTemplates, setShowTemplates] = useState(false)

  const addServer = (template?: MCPTemplate) => {
    const newServer: MCPServerConfig = template ? {
      name: template.name,
      command: template.command,
      args: [...template.args],
      env: template.env ? { ...template.env } : {},
      enabled: true,
    } : {
      name: `MCP Server ${servers.length + 1}`,
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-'],
      env: {},
      enabled: true,
    }

    const id = crypto.randomUUID()
    onChange([...servers, { ...newServer, name: newServer.name }])
    setExpandedId(id)
    setShowTemplates(false)
  }

  const updateServer = (index: number, updates: Partial<MCPServerConfig>) => {
    const newServers = [...servers]
    newServers[index] = { ...newServers[index], ...updates }
    onChange(newServers)
  }

  const removeServer = (index: number) => {
    onChange(servers.filter((_, i) => i !== index))
  }

  const toggleEnabled = (index: number) => {
    updateServer(index, { enabled: !servers[index].enabled })
  }

  const updateArgs = (index: number, argsString: string) => {
    // Parse args, handling quoted strings
    const args = argsString.match(/(?:[^\s"]+|"[^"]*")+/g)?.map(arg =>
      arg.startsWith('"') && arg.endsWith('"') ? arg.slice(1, -1) : arg
    ) || []
    updateServer(index, { args })
  }

  const updateEnv = (index: number, key: string, value: string) => {
    const newEnv = { ...servers[index].env, [key]: value }
    updateServer(index, { env: newEnv })
  }

  const addEnvVar = (index: number) => {
    const newEnv = { ...servers[index].env, NEW_VAR: '' }
    updateServer(index, { env: newEnv })
  }

  const removeEnvVar = (index: number, key: string) => {
    const newEnv = { ...servers[index].env }
    delete newEnv[key]
    updateServer(index, { env: newEnv })
  }

  const renameEnvVar = (index: number, oldKey: string, newKey: string) => {
    const env = servers[index].env
    const value = env[oldKey]
    const newEnv: Record<string, string> = {}
    for (const [k, v] of Object.entries(env)) {
      newEnv[k === oldKey ? newKey : k] = k === oldKey ? value : v
    }
    updateServer(index, { env: newEnv })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-text">MCP Servers</h3>
          <p className="text-xs text-text-muted mt-1">
            Configure Model Context Protocol servers for extended capabilities
          </p>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-primary hover:bg-primary-dark text-white rounded-lg transition-colors"
          >
            <Plus size={16} />
            Add Server
            <ChevronDown size={14} />
          </button>

          {showTemplates && (
            <div className="absolute right-0 top-full mt-1 w-64 bg-surface border border-border rounded-lg shadow-lg z-10">
              <div className="p-2 border-b border-border">
                <button
                  onClick={() => addServer()}
                  className="w-full text-left px-3 py-2 text-sm text-text hover:bg-surface-light rounded"
                >
                  Empty Server
                </button>
              </div>
              <div className="p-2">
                <p className="text-xs text-text-muted px-3 py-1">Templates</p>
                {MCP_TEMPLATES.map((template) => (
                  <button
                    key={template.name}
                    onClick={() => addServer(template)}
                    className="w-full text-left px-3 py-2 hover:bg-surface-light rounded"
                  >
                    <div className="text-sm text-text">{template.name}</div>
                    <div className="text-xs text-text-muted">{template.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Info Banner */}
      <div className="flex items-start gap-2 p-3 bg-primary/10 border border-primary/20 rounded-lg">
        <AlertCircle size={16} className="text-primary mt-0.5" />
        <div className="text-xs text-text-muted">
          <p className="font-medium text-text">MCP servers extend Honolulu&apos;s capabilities</p>
          <p className="mt-1">
            After configuring servers here, restart the backend to apply changes.
            You can also edit <code className="text-primary">config/default.yaml</code> directly.
          </p>
        </div>
      </div>

      {servers.length === 0 ? (
        <div className="text-center py-8 text-text-muted">
          <p>No MCP servers configured</p>
          <p className="text-xs mt-1">Add a server to extend capabilities</p>
        </div>
      ) : (
        <div className="space-y-2">
          {servers.map((server, index) => (
            <div
              key={index}
              className={`border rounded-lg overflow-hidden ${
                server.enabled ? 'border-border' : 'border-border/50 opacity-60'
              }`}
            >
              {/* Header */}
              <div
                className="flex items-center justify-between px-4 py-3 bg-surface-light cursor-pointer"
                onClick={() => setExpandedId(expandedId === String(index) ? null : String(index))}
              >
                <div className="flex items-center gap-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleEnabled(index)
                    }}
                    className={`p-1 rounded ${
                      server.enabled ? 'text-success' : 'text-text-muted'
                    }`}
                    title={server.enabled ? 'Disable' : 'Enable'}
                  >
                    {server.enabled ? <Play size={16} /> : <Square size={16} />}
                  </button>
                  <span className="text-sm font-medium text-text">{server.name}</span>
                  <span className="text-xs text-text-muted">
                    {server.command} {server.args[0]}...
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      removeServer(index)
                    }}
                    className="p-1 text-text-muted hover:text-error transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                  {expandedId === String(index) ? (
                    <ChevronUp size={16} className="text-text-muted" />
                  ) : (
                    <ChevronDown size={16} className="text-text-muted" />
                  )}
                </div>
              </div>

              {/* Expanded Content */}
              {expandedId === String(index) && (
                <div className="p-4 space-y-4 border-t border-border">
                  {/* Name */}
                  <div>
                    <label className="block text-xs text-text-muted mb-1">Name</label>
                    <input
                      type="text"
                      value={server.name}
                      onChange={(e) => updateServer(index, { name: e.target.value })}
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary"
                    />
                  </div>

                  {/* Command */}
                  <div>
                    <label className="block text-xs text-text-muted mb-1">Command</label>
                    <input
                      type="text"
                      value={server.command}
                      onChange={(e) => updateServer(index, { command: e.target.value })}
                      placeholder="npx"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary font-mono"
                    />
                  </div>

                  {/* Args */}
                  <div>
                    <label className="block text-xs text-text-muted mb-1">Arguments</label>
                    <input
                      type="text"
                      value={server.args.map(a => a.includes(' ') ? `"${a}"` : a).join(' ')}
                      onChange={(e) => updateArgs(index, e.target.value)}
                      placeholder="-y @modelcontextprotocol/server-..."
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary font-mono"
                    />
                    <p className="text-xs text-text-muted mt-1">
                      Space-separated arguments. Quote values with spaces.
                    </p>
                  </div>

                  {/* Environment Variables */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs text-text-muted">Environment Variables</label>
                      <button
                        onClick={() => addEnvVar(index)}
                        className="text-xs text-primary hover:underline"
                      >
                        + Add Variable
                      </button>
                    </div>
                    {Object.keys(server.env).length === 0 ? (
                      <p className="text-xs text-text-muted">No environment variables</p>
                    ) : (
                      <div className="space-y-2">
                        {Object.entries(server.env).map(([key, value]) => (
                          <div key={key} className="flex gap-2">
                            <input
                              type="text"
                              value={key}
                              onChange={(e) => renameEnvVar(index, key, e.target.value)}
                              className="flex-1 px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary font-mono"
                              placeholder="KEY"
                            />
                            <input
                              type="text"
                              value={value}
                              onChange={(e) => updateEnv(index, key, e.target.value)}
                              className="flex-[2] px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary font-mono"
                              placeholder="value"
                            />
                            <button
                              onClick={() => removeEnvVar(index, key)}
                              className="p-2 text-text-muted hover:text-error"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
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
