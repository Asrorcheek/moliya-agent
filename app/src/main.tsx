import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import { I18nProvider } from './i18n'
import { AuthProvider } from './lib/authContext'
import { RouterProvider } from './router'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nProvider>
      <AuthProvider>
        <RouterProvider>
          <App />
        </RouterProvider>
      </AuthProvider>
    </I18nProvider>
  </React.StrictMode>,
)
