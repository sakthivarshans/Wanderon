// WanderOn — Tauri main.rs
// Handles: OS keychain, system tray, IPC commands to frontend
// Serves as the Rust host layer in the desktop shell environment.

#![cfg_attr(all(not(debug_assertions), target_os = "windows"), windows_subsystem = "windows")]

use keyring::Entry;
use tauri::{
    CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu,
    SystemTrayMenuItem, WindowEvent,
};

// ── Keychain helpers ────────────────────────────────────────────────────────

/// Saves a secret API key to the host operating system keychain.
#[tauri::command]
fn save_key(service: String, key: String, value: String) -> Result<(), String> {
    let entry = Entry::new(&service, &key).map_err(|e| e.to_string())?;
    entry.set_password(&value).map_err(|e| e.to_string())
}

/// Retrieves a saved API key from the host operating system keychain.
#[tauri::command]
fn load_key(service: String, key: String) -> Result<String, String> {
    let entry = Entry::new(&service, &key).map_err(|e| e.to_string())?;
    entry.get_password().map_err(|e| e.to_string())
}

/// Deletes a saved API key from the host operating system keychain.
#[tauri::command]
fn delete_key(service: String, key: String) -> Result<(), String> {
    let entry = Entry::new(&service, &key).map_err(|e| e.to_string())?;
    entry.delete_password().map_err(|e| e.to_string())
}

/// Verifies whether an API key entry is currently configured in the keychain.
#[tauri::command]
fn check_key_exists(service: String, key: String) -> bool {
    if let Ok(entry) = Entry::new(&service, &key) {
        entry.get_password().is_ok()
    } else {
        false
    }
}

// ── App setup ───────────────────────────────────────────────────────────────

fn build_tray() -> SystemTray {
    let open = CustomMenuItem::new("open", "Open WanderOn");
    let separator = SystemTrayMenuItem::Separator;
    let quit = CustomMenuItem::new("quit", "Quit");

    let menu = SystemTrayMenu::new()
        .add_item(open)
        .add_native_item(separator)
        .add_item(quit);

    SystemTray::new().with_menu(menu)
}

fn main() {
    let tray = build_tray();

    tauri::Builder::default()
        .system_tray(tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::LeftButtonPress { .. } => {
                if let Some(window) = app.get_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "open" => {
                    if let Some(window) = app.get_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "quit" => std::process::exit(0),
                _ => {}
            },
            _ => {}
        })
        .on_window_event(|event| {
            if let WindowEvent::CloseRequested { api, .. } = event.event() {
                // Hide to tray instead of closing
                event.window().hide().unwrap();
                api.prevent_close();
            }
        })
        .invoke_handler(tauri::generate_handler![
            save_key,
            load_key,
            delete_key,
            check_key_exists
        ])
        .run(tauri::generate_context!())
        .expect("error while running WanderOn");
}
