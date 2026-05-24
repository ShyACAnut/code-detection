import React from 'react';
import ReactDOM from 'react-dom/client';
import { AuthProvider } from './contexts/AuthContext';
import App from './App1';
import * as monaco from 'monaco-editor';

self.MonacoEnvironment = {
  getWorkerUrl: function (moduleId: string, label: string) {
    if (label === 'json') {
      return 'https://cdn.jsdelivr.net/npm/monaco-editor@0.55.1/min/vs/language/json/json.worker.js';
    }
    if (label === 'css' || label === 'scss' || label === 'less') {
      return 'https://cdn.jsdelivr.net/npm/monaco-editor@0.55.1/min/vs/language/css/css.worker.js';
    }
    if (label === 'html' || label === 'handlebars' || label === 'razor') {
      return 'https://cdn.jsdelivr.net/npm/monaco-editor@0.55.1/min/vs/language/html/html.worker.js';
    }
    if (label === 'typescript' || label === 'javascript') {
      return 'https://cdn.jsdelivr.net/npm/monaco-editor@0.55.1/min/vs/language/typescript/ts.worker.js';
    }
    return 'https://cdn.jsdelivr.net/npm/monaco-editor@0.55.1/min/vs/editor/editor.worker.js';
  }
};

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <AuthProvider>
      <App/>
    </AuthProvider>
  </React.StrictMode>
);