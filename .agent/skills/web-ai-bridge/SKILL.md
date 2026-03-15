---
name: web-ai-bridge
description: Mandatory bridge protocol for treating Web LLM GUIs (Gemini, ChatGPT, Copilot) as autonomous agentic inference engines. Trigger for any task involving browser-based AI automation, DOM-based prompt injection, real-time response scraping, or WebSocket bridge maintenance.
---

# Web AI Bridge Protocol

This skill defines the technical specifications for bypassing API limitations by using high-performance DOM manipulation to treat web-based AI interfaces as headless inference engines.

## 1. Connection Architecture (WebSocket Bridge)

- **Transport Layer**: Bidirectional WebSocket connection via `ws://127.0.0.1:6090`.
- **Background Persistence (MV3)**: To bypass the 30-second Service Worker expiration in Chrome Manifest V3:
    - `chrome.alarms` trigger every 30s.
    - `port.postMessage` heartbeat every 25s.
- **Context Isolation**: All UI overlays Must use Shadow DOM with `mode: "closed"` to prevent target site CSS leakage and DOM interference.

## 2. Injection Protocol (4-Tier Input Strategy)

To ensure reliable text delivery into `contenteditable` rich-text areas, the following fallback chain MUST be followed:

1.  **Native Strategy**: `document.execCommand("insertText")` followed by `execCommand("insertLineBreak")` to simulate Shift+Enter and avoid paragraph bloating.
2.  **Clipboard Strategy**: Construct a `DataTransfer` object and dispatch a `ClipboardEvent("paste")` to bypass script-based input guards.
3.  **HTML Strategy**: `execCommand("insertHTML")` with direct `<br>` injection for precise layout control.
4.  **Force-Reset Strategy**: Wipe target DOM, generate atomic `<p>` tags, and manually dispatch `InputEvent` to force underlying React/Angular state synchronization.

## 3. Extraction Protocol (Real-time Scraping)

- **Polling Frequency**: 100ms interval monitoring of the assistant-role DOM (e.g., `.model-response` for Gemini).
- **Dynamic Selection**: Selctors MUST be re-queried on every tick to handle React/Angular DOM reconciliation that breaks existing node references.
- **Completion Detection**:
    - **Pattern A (Active)**: Monitor for the disappearance of the "Stop streaming" button + 500ms of text stability.
    - **Pattern B (Passive)**: 1500ms of text stability after a mandatory 2s initial generation window.
- **Safety**: Enforcement of a 300s hard timeout per inference cycle.

## 4. Site Registry (Selector Mapping)

| Site | Input Area Selector | Send Button Selector | Response Container |
| :--- | :--- | :--- | :--- |
| **Gemini** | `input-area-v2 [contenteditable]` | `button[aria-label*="送信"]` | `model-response` |
| **ChatGPT** | `#prompt-textarea` | `button[data-testid="send-button"]` | `[data-message-author-role="assistant"]` |
| **Copilot** | `textarea[placeholder*="Copilot"]` | `button[aria-label="Submit"]` | `[data-testid="chat-message"]` |

## 5. Agentic Principles

- **Human Emulation**: Always add a `300ms` delay after injection to allow the site to enable the Send button, and `1000ms` after submission to wait for the response DOM to initialize.
- **Success Path Only**: Do not implement complex error handling; let the higher-level agent retry the inference if the bridge times out or returns empty data.
