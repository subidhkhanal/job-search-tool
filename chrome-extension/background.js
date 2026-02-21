// Service worker — initialize default profile on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get("profile", (data) => {
    if (!data.profile) {
      chrome.storage.local.set({
        profile: {
          fullName: "Subidh Khanal",
          email: "subidhkhanal38@gmail.com",
          phone: "+91-8527394809",
          linkedin: "https://linkedin.com/in/subidh-khanal",
          github: "",
          portfolio: "",
          location: "Noida, India",
          currentRole: "AI Engineer Intern",
          experience: "Fresher",
          skills: "Python, LangChain, RAG, FastAPI, OpenAI API, ChromaDB, Next.js, Agentic AI"
        }
      });
    }
  });
});
