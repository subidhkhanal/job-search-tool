// Content script — listens for fill requests from the popup
// The actual filling logic is injected via chrome.scripting.executeScript
// from popup.js, so this script only needs to be present for message handling

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "ping") {
    sendResponse({ status: "ready" });
  }
  if (request.action === "detectPlatform") {
    sendResponse({ platform: detectPlatform() });
  }
});

function detectPlatform() {
  const hostname = window.location.hostname;
  if (hostname.includes("naukri.com")) return "naukri";
  if (hostname.includes("internshala.com")) return "internshala";
  if (hostname.includes("cutshort.io")) return "cutshort";
  if (hostname.includes("wellfound.com")) return "wellfound";
  if (hostname.includes("linkedin.com")) return "linkedin";
  if (hostname.includes("instahyre.com")) return "instahyre";
  return "generic";
}
