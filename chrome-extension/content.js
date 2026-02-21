// Content script — listens for fill requests from the popup
// The actual filling logic is injected via chrome.scripting.executeScript
// from popup.js, so this script only needs to be present for message handling

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "ping") {
    sendResponse({ status: "ready" });
  }
});
