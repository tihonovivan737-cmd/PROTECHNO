var _a;
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Бэкенд: uvicorn backend.app.main:app --reload → http://127.0.0.1:8000
// Можно переопределить адрес бэка переменной окружения VITE_BACKEND_TARGET
// (полезно, если uvicorn запущен на другом хосте/порту).
var BACKEND_TARGET = (_a = process.env.VITE_BACKEND_TARGET) !== null && _a !== void 0 ? _a : "http://127.0.0.1:8000";
export default defineConfig({
    plugins: [react()],
    server: {
        // host: true — Vite слушает 0.0.0.0, заходить с любого устройства в LAN
        // по http://<ip-машины>:5173. /api проксируется в uvicorn.
        host: true,
        port: 5173,
        strictPort: true,
        proxy: {
            "/api": {
                target: BACKEND_TARGET,
                changeOrigin: true,
            },
        },
    },
    preview: {
        // vite preview — отдача собранного билда тоже на 0.0.0.0
        host: true,
        port: 4173,
        strictPort: true,
    },
});
