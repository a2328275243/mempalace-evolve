const { contextBridge, ipcRenderer } = require('electron')

const allowedInvokeChannels = new Set([
  'status:get',
  'project:list',
  'project:choose',
  'project:save',
  'project:delete',
  'project:active',
  'provider:list',
  'provider:save',
  'provider:delete',
  'provider:active',
  'provider:test',
  'provider:diagnose',
  'history:status',
  'history:list',
  'history:search',
  'history:show',
  'workspace:changes',
  'workspace:diff',
  'task:run',
  'task:cancel',
  'terminal:open',
  'terminal:check',
  'terminal:run',
  'doctor:run',
  'memory:audit',
  'evolve:status',
  'desktop:threads:list',
  'desktop:threads:create',
  'desktop:threads:update',
  'desktop:threads:select',
  'desktop:tasks:list',
  'desktop:tasks:upsert',
  'desktop:settings:update',
  'desktop:artifacts:list',
  'desktop:artifacts:add',
  'desktop:openPath',
])

const allowedEventChannels = new Set([
  'task:output',
])

contextBridge.exposeInMainWorld('dreamseed', {
  invoke: (channel, payload) => {
    if (!allowedInvokeChannels.has(channel)) {
      throw new Error(`DreamSeed desktop channel is not allowed: ${channel}`)
    }
    return ipcRenderer.invoke(channel, payload)
  },
  onEvent: (channel, callback) => {
    if (!allowedEventChannels.has(channel)) {
      throw new Error(`DreamSeed desktop event channel is not allowed: ${channel}`)
    }
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on(channel, listener)
    return () => ipcRenderer.removeListener(channel, listener)
  },
})
