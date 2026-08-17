export interface PickerConfig {
  access_token: string
  developer_key: string
  client_id: string
}

export interface PickedSpreadsheet {
  id: string
  name: string
}

type PickerDocument = { id?: string; name?: string }
type PickerData = { action?: string; docs?: PickerDocument[] }

type PickerBuilder = {
  addView: (view: unknown) => PickerBuilder
  setOAuthToken: (token: string) => PickerBuilder
  setDeveloperKey: (key: string) => PickerBuilder
  setCallback: (callback: (data: PickerData) => void) => PickerBuilder
  build: () => { setVisible: (visible: boolean) => void }
}

type PickerNamespace = {
  Action: { PICKED: string; CANCEL: string }
  ViewId: { SPREADSHEETS: string }
  DocsView: new (viewId: string) => unknown
  PickerBuilder: new () => PickerBuilder
}

declare global {
  interface Window {
    gapi?: { load: (name: string, callback: () => void) => void }
    google?: { picker: PickerNamespace }
  }
}

function loadPickerLibrary(): Promise<PickerNamespace> {
  return new Promise((resolve, reject) => {
    const ready = () => {
      window.gapi?.load('picker', () => {
        if (window.google?.picker) resolve(window.google.picker)
        else reject(new Error('Google Picker yuklanmadi'))
      })
    }
    if (window.gapi) { ready(); return }
    const existing = document.querySelector<HTMLScriptElement>('#google-picker-api')
    if (existing) {
      existing.addEventListener('load', ready, { once: true })
      existing.addEventListener('error', () => reject(new Error('Google API yuklanmadi')), { once: true })
      return
    }
    const script = document.createElement('script')
    script.id = 'google-picker-api'
    script.src = 'https://apis.google.com/js/api.js'
    script.async = true
    script.onload = ready
    script.onerror = () => reject(new Error('Google API yuklanmadi'))
    document.head.appendChild(script)
  })
}

export async function pickGoogleSpreadsheet(
  config: PickerConfig,
): Promise<PickedSpreadsheet | null> {
  const picker = await loadPickerLibrary()
  return new Promise((resolve) => {
    const view = new picker.DocsView(picker.ViewId.SPREADSHEETS)
    const instance = new picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(config.access_token)
      .setDeveloperKey(config.developer_key)
      .setCallback((data) => {
        if (data.action === picker.Action.CANCEL) { resolve(null); return }
        if (data.action !== picker.Action.PICKED) return
        const document = data.docs?.[0]
        resolve(document?.id ? { id: document.id, name: document.name || 'Google Sheet' } : null)
      })
      .build()
    instance.setVisible(true)
  })
}
