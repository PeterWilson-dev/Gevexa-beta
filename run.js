#!/usr/bin/env node
/**
 * Gevexa-beta CLI — A futuristic terminal AI assistant.
 * Requires: blessed
 * Run: node run.js
 */

const fs   = require("fs");
const path = require("path");
const blessed = require("blessed");

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────
const BRAIN_FILE = path.join(__dirname, "brain.json");
const APP_NAME   = "Gevexa-beta";
const VERSION    = "v1.0.0";
const AI_NAME    = "Gevexa-beta";

const GEVEXA_LOGO = [
  "  ░██████╗░███████╗██╗░░░██╗███████╗██╗░░██╗░█████╗░  ",
  "  ██╔════╝░██╔════╝██║░░░██║██╔════╝╚██╗██╔╝██╔══██╗  ",
  "  ██║░░██╗░█████╗░░╚██╗░██╔╝█████╗░░░╚███╔╝░███████║  ",
  "  ██║░░╚██╗██╔══╝░░░╚████╔╝░██╔══╝░░░██╔██╗░██╔══██║  ",
  "  ╚██████╔╝███████╗░░╚██╔╝░░███████╗██╔╝╚██╗██║░░██║  ",
  "  ░╚═════╝░╚══════╝░░░╚═╝░░░╚══════╝╚═╝░░╚═╝╚═╝░░╚═╝  ",
];

// ─────────────────────────────────────────────
// LOAD BRAIN
// ─────────────────────────────────────────────
function loadBrain() {
  try {
    if (fs.existsSync(BRAIN_FILE)) {
      const raw = fs.readFileSync(BRAIN_FILE, "utf-8");
      return JSON.parse(raw);
    }
  } catch (_) {}
  return {};
}

const brain = loadBrain();

// ─────────────────────────────────────────────
// AI LOGIC
// ─────────────────────────────────────────────
function queryBrain(userInput) {
  const normalized = userInput.trim().toLowerCase();
  if (brain[normalized]) return brain[normalized];
  for (const [key, val] of Object.entries(brain)) {
    if (key.includes(normalized) || normalized.includes(key)) return val;
  }
  return "I don't understand. Try typing 'help' to see what I know.";
}

// ─────────────────────────────────────────────
// CHAT STATE
// ─────────────────────────────────────────────
const chatHistory = []; // { role: 'you'|'ai'|'system', msg: string }
let isThinking    = false;
let statusMessage = "";

// ─────────────────────────────────────────────
// GEVEXA CLI CLASS
// ─────────────────────────────────────────────
class GevexaCLI {
  constructor() {
    this.screen      = null;
    this.headerBox   = null;
    this.chatBox     = null;
    this.inputBox    = null;
    this.statusBar   = null;
    this.typingTimer = null;
  }

  // ── helpers ──────────────────────────────
  _refresh() {
    if (this.screen) this.screen.render();
  }

  _scrollToBottom() {
    if (this.chatBox) this.chatBox.setScrollPerc(100);
  }

  _addMessage(role, msg) {
    chatHistory.push({ role, msg });
    this._renderChat();
    this._scrollToBottom();
    this._refresh();
  }

  // ── chat renderer ─────────────────────────
  _renderChat() {
    if (!this.chatBox) return;

    const lines = [];

    if (!chatHistory.length && !isThinking) {
      lines.push("{#4b4b6b-fg}  Start a conversation -- type something below and press Enter{/}");
    }

    for (const { role, msg } of chatHistory) {
      if (role === "you") {
        lines.push(`{bold}{#818cf8-fg}  You             > {/}{#a5b4fc-fg}${msg}{/}`);
        lines.push("");
      } else if (role === "ai") {
        const msgLines = msg.split("\n");
        msgLines.forEach((line, i) => {
          const prefix = i === 0 ? `{bold}{#c084fc-fg}  ${AI_NAME}  > {/}` : `{#c084fc-fg}                    {/}`;
          lines.push(`${prefix}{#e9d5ff-fg}${line}{/}`);
        });
        lines.push("");
      } else if (role === "system") {
        lines.push(`{#6b7280-fg}  [sys]  ${msg}{/}`);
        lines.push("");
      }
    }

    if (isThinking) {
      lines.push(`{italic}{#7c3aed-fg}  ${AI_NAME}  >   ${statusMessage}{/}`);
      lines.push("");
    }

    this.chatBox.setContent(lines.join("\n"));
    this._scrollToBottom();
  }

  // ── typing animation ─────────────────────
  _typeResponse(response) {
    isThinking = true;
    let dotCount = 0;

    const thinkInterval = setInterval(() => {
      dotCount = (dotCount % 3) + 1;
      statusMessage = "thinking" + ".".repeat(dotCount);
      this._renderChat();
      this._refresh();
    }, 250);

    // After ~0.8s of "thinking...", start typing
    setTimeout(() => {
      clearInterval(thinkInterval);
      let typed = "";
      const delay = Math.max(10, Math.min(30, Math.floor(1200 / Math.max(response.length, 1))));
      let charIndex = 0;

      const typeInterval = setInterval(() => {
        if (charIndex >= response.length) {
          clearInterval(typeInterval);
          isThinking = false;
          statusMessage = "";
          this._addMessage("ai", response);
          this._refresh();
          if (this.inputBox) this.inputBox.focus();
          return;
        }
        typed += response[charIndex++];
        statusMessage = typed + "|";
        this._renderChat();
        this._refresh();
      }, delay);
    }, 800);
  }

  // ── input handler ────────────────────────
  _handleInput(text) {
    const stripped = text.trim();
    if (!stripped) return;

    if (stripped.toLowerCase() === "exit") {
      this._exit();
      return;
    }

    if (stripped.toLowerCase() === "/clear") {
      chatHistory.length = 0;
      this._renderChat();
      this._refresh();
      return;
    }

    this._addMessage("you", stripped);

    if (!isThinking) {
      this._typeResponse(queryBrain(stripped));
    }
  }

  // ── exit ─────────────────────────────────
  _exit() {
    if (this.screen) {
      this.screen.destroy();
    }
    console.clear();
    console.log("\x1b[35m╔══════════════════════════════════════════════╗\x1b[0m");
    console.log(`\x1b[35m║  \x1b[1m\x1b[95mSession ended. Thanks for using ${APP_NAME}.\x1b[0m\x1b[35m  ║\x1b[0m`);
    console.log("\x1b[35m╚══════════════════════════════════════════════╝\x1b[0m");
    process.exit(0);
  }

  // ── build layout ─────────────────────────
  _buildLayout() {
    this.screen = blessed.screen({
      smartCSR: true,
      title: `${APP_NAME} ${VERSION}`,
      fullUnicode: true,
      mouse: true,
    });

    // Header box
    const headerContent = [
      ...GEVEXA_LOGO.map(l => `{#a855f7-fg}${l}{/}`),
      `{#7c3aed-fg}  ${"─".repeat(56)}{/}`,
      `{#6b7280-fg}  ${VERSION}  --  terminal AI  --  type {/}{bold}{#a855f7-fg}help{/}{#6b7280-fg} to get started{/}`,
    ].join("\n");

    this.headerBox = blessed.box({
      top: 0,
      left: 0,
      width: "100%",
      height: 9,
      content: headerContent,
      tags: true,
      style: { fg: "#d8d8e8", bg: "#08080f" },
    });

    // Chat frame + box
    const chatFrame = blessed.box({
      top: 9,
      left: 0,
      width: "100%",
      height: "100%-16",
      border: { type: "line" },
      label: " Conversation ",
      tags: true,
      style: {
        border: { fg: "#7c3aed" },
        label:  { bold: true, fg: "#a855f7" },
        bg: "#08080f",
        fg: "#d8d8e8",
      },
    });

    this.chatBox = blessed.box({
      parent: chatFrame,
      top: 0,
      left: 0,
      width: "100%-2",
      height: "100%-2",
      scrollable: true,
      alwaysScroll: true,
      tags: true,
      mouse: true,
      scrollbar: {
        ch: "█",
        style: { fg: "#7c3aed", bg: "#1a1a2e" },
      },
      style: { bg: "#08080f", fg: "#d8d8e8" },
    });

    // Input frame + area
    const inputFrame = blessed.box({
      bottom: 1,
      left: 0,
      width: "100%",
      height: 5,
      border: { type: "line" },
      label: " Message ",
      tags: true,
      style: {
        border: { fg: "#7c3aed" },
        label:  { bold: true, fg: "#a855f7" },
        bg: "#0c0c18",
      },
    });

    this.inputBox = blessed.textbox({
      parent: inputFrame,
      top: 0,
      left: 0,
      width: "100%-2",
      height: "100%-2",
      inputOnFocus: true,
      keys: true,
      mouse: true,
      style: { bg: "#0c0c18", fg: "#d8d8e8" },
    });

    // Status bar
    this.statusBar = blessed.box({
      bottom: 0,
      left: 0,
      width: "100%",
      height: 1,
      content:
        "  {bold}{#a855f7-fg}Enter{/} {#4b4b6b-fg}send    {/}" +
        "{bold}{#a855f7-fg}/clear{/} {#4b4b6b-fg}clear    {/}" +
        "{bold}{#a855f7-fg}exit{/} {#4b4b6b-fg}quit    {/}" +
        "{bold}{#a855f7-fg}Ctrl+C{/} {#4b4b6b-fg}force quit{/}",
      tags: true,
      style: { bg: "#0f0f1a", fg: "#4b4b6b" },
    });

    // Append to screen
    this.screen.append(this.headerBox);
    this.screen.append(chatFrame);
    this.screen.append(inputFrame);
    this.screen.append(this.statusBar);
  }

  // ── keybindings ──────────────────────────
  _buildKeybindings() {
    // Submit on Enter
    this.inputBox.key("enter", () => {
      const text = this.inputBox.getValue();
      this.inputBox.clearValue();
      this._handleInput(text);
      this._refresh();
    });

    // Ctrl+C / Ctrl+Q to quit
    this.screen.key(["C-c", "C-q"], () => this._exit());

    // Ctrl+L to clear chat
    this.screen.key("C-l", () => {
      chatHistory.length = 0;
      this._renderChat();
      this._refresh();
    });
  }

  // ── run ──────────────────────────────────
  run() {
    // Check blessed is installed
    try {
      require.resolve("blessed");
    } catch (_) {
      console.error("Missing dependency: blessed");
      console.error("Install with: npm install blessed");
      process.exit(1);
    }

    this._buildLayout();
    this._buildKeybindings();

    // Initial system message
    chatHistory.push({
      role: "system",
      msg:  `${APP_NAME} ${VERSION} initialized -- brain.json loaded (${Object.keys(brain).length} entries)`,
    });

    this._renderChat();
    this.inputBox.focus();
    this._refresh();
  }
}

// ─────────────────────────────────────────────
// ENTRY POINT
// ─────────────────────────────────────────────
const cli = new GevexaCLI();
cli.run();
