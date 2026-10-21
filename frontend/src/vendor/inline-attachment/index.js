/**
 * Vendored/customized inline-attachment helpers for markdown editors.
 *
 * - core.js: upload helpers + classic window.inlineAttachment API
 * - codemirror4.js: CodeMirror 4 adapter (registers editors.codemirror4)
 *
 * Import order matters: core must load before the CodeMirror adapter.
 */
import "./core";
import "./codemirror4";

export { DEFAULT_SETTINGS, initSettings, isFileAllowed, uploadFile } from "./core";
