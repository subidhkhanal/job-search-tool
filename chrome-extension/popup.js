const DEFAULT_PROFILE = {
  fullName: "Subidh Khanal",
  email: "subidhkhanal38@gmail.com",
  phone: "+91-8527394809",
  linkedin: "https://linkedin.com/in/subidh-khanal",
  github: "",
  portfolio: "",
  location: "Noida, India",
  currentRole: "AI Engineer Intern",
  experience: "Fresher",
  skills: "Python, LangChain, RAG, FastAPI, OpenAI API, ChromaDB, Next.js, Agentic AI",
  coverLetter: "I'm an AI Engineer building production LLM systems. Currently interning at PathToPR.ca where I built automated content pipelines using OpenAI and Gemini APIs. My main project is an Agentic RAG Knowledge Base with hybrid retrieval, query routing, and RAGAS evaluation — built with LangChain, FastAPI, ChromaDB, and Next.js. I also run BCT Engineering Notes, Nepal's most popular CS blog with 2.2M+ views. I'd love to bring this experience to your team."
};

const FIELD_IDS = [
  "fullName", "email", "phone", "linkedin", "github",
  "portfolio", "location", "currentRole", "experience", "skills", "coverLetter"
];

// Platform-specific selectors
const PLATFORM_SELECTORS = {
  naukri: {
    name: ["#name", 'input[name="name"]', 'input[placeholder*="name" i]'],
    email: ["#email", 'input[name="email"]', 'input[type="email"]'],
    phone: ["#mobile", 'input[name="mobile"]', 'input[name="phone"]'],
    experience: ['#experience select', 'select[name="experience"]'],
    currentSalary: ['#currentSalary', 'input[name="currentSalary"]'],
    expectedSalary: ['#expectedSalary', 'input[name="expectedSalary"]'],
    noticePeriod: ['select[name="noticePeriod"]'],
    location: ['#location', 'input[name="location"]'],
    defaults: { experience: "Fresher", noticePeriod: "Immediate", location: "Noida" }
  },
  internshala: {
    name: ['input[name="student_name"]', "#student_name"],
    email: ['input[name="student_email"]', "#student_email"],
    phone: ['input[name="student_mobile"]', "#student_mobile"],
    coverLetter: ['textarea[name="cover_letter"]', "#cover_letter"],
    linkedin: ['input[name="linkedin"]', 'input[placeholder*="linkedin" i]'],
    github: ['input[name="github"]', 'input[placeholder*="github" i]'],
    availability: ['input[name="availability"]'],
  },
  wellfound: {
    name: ['input[aria-label*="name" i]', 'input[placeholder*="name" i]'],
    email: ['input[aria-label*="email" i]', 'input[type="email"]'],
    linkedin: ['input[aria-label*="linkedin" i]', 'input[placeholder*="linkedin" i]'],
    website: ['input[aria-label*="website" i]', 'input[placeholder*="portfolio" i]'],
    resume: ['input[type="file"]'],
    whyInterested: ['textarea[aria-label*="interested" i]', 'textarea[placeholder*="interested" i]'],
  },
};

// DOM refs
const mainView = document.getElementById("main-view");
const settingsView = document.getElementById("settings-view");
const fillBtn = document.getElementById("fill-btn");
const coverLetterBtn = document.getElementById("cover-letter-btn");
const settingsBtn = document.getElementById("settings-btn");
const backBtn = document.getElementById("back-btn");
const settingsForm = document.getElementById("settings-form");
const statusEl = document.getElementById("status");
const saveStatusEl = document.getElementById("save-status");
const displayName = document.getElementById("display-name");
const displayEmail = document.getElementById("display-email");
const platformInfo = document.getElementById("platform-info");
const fillSummary = document.getElementById("fill-summary");

// Load profile from storage
function loadProfile() {
  return new Promise((resolve) => {
    chrome.storage.local.get("profile", (data) => {
      resolve(data.profile || DEFAULT_PROFILE);
    });
  });
}

// Save profile to storage
function saveProfile(profile) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ profile }, resolve);
  });
}

// Show status message
function showStatus(el, message, type) {
  el.textContent = message;
  el.className = `status ${type}`;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 4000);
}

// Detect platform on the active tab
async function detectCurrentPlatform() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = new URL(tab.url);
    const hostname = url.hostname;
    if (hostname.includes("naukri.com")) return "naukri";
    if (hostname.includes("internshala.com")) return "internshala";
    if (hostname.includes("cutshort.io")) return "cutshort";
    if (hostname.includes("wellfound.com")) return "wellfound";
    if (hostname.includes("linkedin.com")) return "linkedin";
    if (hostname.includes("instahyre.com")) return "instahyre";
    return "generic";
  } catch {
    return "generic";
  }
}

// Initialize popup
async function init() {
  const profile = await loadProfile();
  displayName.textContent = profile.fullName || "Set up your profile";
  displayEmail.textContent = profile.email || "Click settings to get started";

  // Detect and show platform
  const platform = await detectCurrentPlatform();
  const platformNames = {
    naukri: "Naukri.com", internshala: "Internshala", cutshort: "Cutshort",
    wellfound: "Wellfound", linkedin: "LinkedIn", instahyre: "Instahyre",
    generic: "Generic"
  };
  platformInfo.textContent = `Platform: ${platformNames[platform] || platform}`;
}

// Fill form button
fillBtn.addEventListener("click", async () => {
  const profile = await loadProfile();
  const platform = await detectCurrentPlatform();

  fillBtn.disabled = true;
  fillBtn.textContent = "Filling...";

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: fillFormFields,
      args: [profile, platform]
    });

    const result = results[0]?.result;
    if (result) {
      showStatus(statusEl, `Filled ${result.filled}/${result.total} fields`, "success");

      // Show fill summary
      if (result.details) {
        let html = `<strong>Filled on ${result.platformName}:</strong><br>`;
        for (const d of result.details) {
          html += d.filled
            ? `<span class="fill-ok">${d.field} ✓</span> `
            : `<span class="fill-miss">${d.field} ✗</span> `;
        }
        fillSummary.innerHTML = html;
        fillSummary.classList.remove("hidden");
      }
    } else {
      showStatus(statusEl, "No form fields found on this page", "info");
    }
  } catch (err) {
    showStatus(statusEl, "Cannot fill on this page (restricted)", "error");
  }

  fillBtn.disabled = false;
  fillBtn.textContent = "Fill Form";
});

// Cover letter button
coverLetterBtn.addEventListener("click", async () => {
  const profile = await loadProfile();
  const coverText = profile.coverLetter || DEFAULT_PROFILE.coverLetter;

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: pasteCoverLetter,
      args: [coverText]
    });

    const result = results[0]?.result;
    if (result?.pasted) {
      showStatus(statusEl, "Cover letter pasted!", "success");
    } else {
      showStatus(statusEl, "No cover letter field found", "info");
    }
  } catch (err) {
    showStatus(statusEl, "Cannot paste on this page", "error");
  }
});

// Settings navigation
settingsBtn.addEventListener("click", async () => {
  const profile = await loadProfile();
  FIELD_IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = profile[id] || "";
  });
  mainView.classList.add("hidden");
  settingsView.classList.remove("hidden");
});

backBtn.addEventListener("click", () => {
  settingsView.classList.add("hidden");
  mainView.classList.remove("hidden");
  init();
});

// Save settings
settingsForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const profile = {};
  FIELD_IDS.forEach((id) => {
    const el = document.getElementById(id);
    profile[id] = el ? el.value.trim() : "";
  });
  await saveProfile(profile);
  showStatus(saveStatusEl, "Saved!", "success");
});

// Function to paste cover letter into textarea
function pasteCoverLetter(coverText) {
  const coverPatterns = [
    "cover_letter", "cover-letter", "coverletter", "cover letter",
    "motivation", "why_interested", "why-interested", "message",
    "additional_info", "additional-info", "note"
  ];

  const textareas = document.querySelectorAll("textarea");
  for (const ta of textareas) {
    const sig = [
      ta.getAttribute("name"), ta.getAttribute("id"),
      ta.getAttribute("placeholder"), ta.getAttribute("aria-label"),
    ].filter(Boolean).map(s => s.toLowerCase()).join(" ");

    if (coverPatterns.some(p => sig.includes(p))) {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, "value"
      )?.set;
      if (nativeSetter) nativeSetter.call(ta, coverText);
      else ta.value = coverText;
      ta.dispatchEvent(new Event("input", { bubbles: true }));
      ta.dispatchEvent(new Event("change", { bubbles: true }));
      ta.style.outline = "2px solid #4caf50";
      return { pasted: true };
    }
  }

  // Fallback: paste into the first large empty textarea
  for (const ta of textareas) {
    if (!ta.value && ta.offsetParent !== null && ta.rows >= 3) {
      const nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, "value"
      )?.set;
      if (nativeSetter) nativeSetter.call(ta, coverText);
      else ta.value = coverText;
      ta.dispatchEvent(new Event("input", { bubbles: true }));
      ta.dispatchEvent(new Event("change", { bubbles: true }));
      ta.style.outline = "2px solid #4caf50";
      return { pasted: true };
    }
  }

  return { pasted: false };
}

// The function injected into the page
function fillFormFields(profile, platform) {
  const platformNames = {
    naukri: "Naukri.com", internshala: "Internshala", cutshort: "Cutshort",
    wellfound: "Wellfound", linkedin: "LinkedIn", instahyre: "Instahyre",
    generic: "Generic"
  };

  // Platform-specific direct selectors (try these first)
  const PLATFORM_DIRECT = {
    naukri: [
      { field: "Name", selectors: ["#name", 'input[name="name"]'], value: profile.fullName },
      { field: "Email", selectors: ["#email", 'input[name="email"]', 'input[type="email"]'], value: profile.email },
      { field: "Phone", selectors: ["#mobile", 'input[name="mobile"]', 'input[name="phone"]'], value: profile.phone },
      { field: "Location", selectors: ["#location", 'input[name="location"]'], value: "Noida" },
    ],
    internshala: [
      { field: "Name", selectors: ['input[name="student_name"]', "#student_name"], value: profile.fullName },
      { field: "Email", selectors: ['input[name="student_email"]', "#student_email"], value: profile.email },
      { field: "Phone", selectors: ['input[name="student_mobile"]', "#student_mobile"], value: profile.phone },
      { field: "LinkedIn", selectors: ['input[name="linkedin"]', 'input[placeholder*="linkedin" i]'], value: profile.linkedin },
      { field: "GitHub", selectors: ['input[name="github"]', 'input[placeholder*="github" i]'], value: profile.github },
    ],
    wellfound: [
      { field: "Name", selectors: ['input[aria-label*="name" i]', 'input[placeholder*="name" i]'], value: profile.fullName },
      { field: "Email", selectors: ['input[aria-label*="email" i]', 'input[type="email"]'], value: profile.email },
      { field: "LinkedIn", selectors: ['input[aria-label*="linkedin" i]', 'input[placeholder*="linkedin" i]'], value: profile.linkedin },
      { field: "Website", selectors: ['input[aria-label*="website" i]', 'input[placeholder*="portfolio" i]'], value: profile.portfolio },
    ],
  };

  const FIELD_MATCHERS = {
    fullName: {
      patterns: ["name", "full_name", "full-name", "fullname", "applicant_name", "applicant-name", "your_name", "your-name", "candidate_name"],
      excludePatterns: ["company", "last_name", "last-name", "first_name", "first-name", "user_name", "username", "middle"],
      value: profile.fullName
    },
    firstName: {
      patterns: ["first_name", "first-name", "firstname", "given_name", "given-name", "fname"],
      excludePatterns: [],
      value: profile.fullName ? profile.fullName.split(" ")[0] : ""
    },
    lastName: {
      patterns: ["last_name", "last-name", "lastname", "surname", "family_name", "family-name", "lname"],
      excludePatterns: [],
      value: profile.fullName ? profile.fullName.split(" ").slice(1).join(" ") : ""
    },
    email: {
      patterns: ["email", "e-mail", "email_address", "emailaddress"],
      excludePatterns: ["confirm", "verify", "company"],
      value: profile.email
    },
    phone: {
      patterns: ["phone", "mobile", "contact", "tel", "telephone", "cell", "phone_number", "phonenumber", "contact_number"],
      excludePatterns: ["company"],
      value: profile.phone
    },
    linkedin: {
      patterns: ["linkedin", "linked_in", "linkedin_url", "linkedin-url", "linkedinurl", "social"],
      excludePatterns: ["twitter", "facebook", "github"],
      value: profile.linkedin
    },
    github: {
      patterns: ["github", "git_hub", "github_url", "github-url", "githuburl"],
      excludePatterns: ["linkedin", "twitter"],
      value: profile.github
    },
    portfolio: {
      patterns: ["portfolio", "website", "personal_website", "personal-website", "blog", "portfolio_url"],
      excludePatterns: ["company"],
      value: profile.portfolio
    },
    location: {
      patterns: ["location", "city", "current_location", "current-location", "currentlocation", "address", "current_city"],
      excludePatterns: ["company", "job", "preferred", "zip", "postal", "state", "country"],
      value: profile.location
    },
    currentRole: {
      patterns: ["current_role", "current-role", "currentrole", "current_title", "current-title", "job_title", "title", "designation", "headline", "current_position"],
      excludePatterns: ["company", "desired", "expected"],
      value: profile.currentRole
    },
    experience: {
      patterns: ["experience", "years_experience", "years-experience", "total_experience", "work_experience", "exp", "yoe"],
      excludePatterns: [],
      value: profile.experience
    },
    skills: {
      patterns: ["skills", "skill", "tech_stack", "tech-stack", "technologies", "key_skills", "key-skills", "technical_skills", "competencies"],
      excludePatterns: [],
      value: profile.skills
    }
  };

  function getFieldSignature(el) {
    const attrs = [
      el.getAttribute("name"),
      el.getAttribute("id"),
      el.getAttribute("placeholder"),
      el.getAttribute("aria-label"),
      el.getAttribute("autocomplete"),
      el.getAttribute("data-field"),
      el.getAttribute("data-name")
    ];
    const labelEl = el.labels?.[0] || (el.id && document.querySelector(`label[for="${el.id}"]`));
    if (labelEl) attrs.push(labelEl.textContent);
    return attrs.filter(Boolean).map(s => s.toLowerCase().trim()).join(" ");
  }

  function matchField(signature, matcher) {
    for (const excl of matcher.excludePatterns) {
      if (signature.includes(excl)) return false;
    }
    for (const pattern of matcher.patterns) {
      if (signature.includes(pattern)) return true;
    }
    return false;
  }

  function isVisible(el) {
    if (el.offsetParent === null && getComputedStyle(el).position !== "fixed") return false;
    const style = getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
  }

  function setNativeValue(el, value) {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, "value"
    )?.set || Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype, "value"
    )?.set;
    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(el, value);
    } else {
      el.value = value;
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  function handleSelect(el, matcher) {
    const options = Array.from(el.options);
    const searchTerms = matcher.value.toLowerCase().split(/[\s,]+/);
    let bestMatch = null;
    let bestScore = 0;

    for (const option of options) {
      if (option.disabled || option.value === "") continue;
      const text = (option.text + " " + option.value).toLowerCase();
      let score = 0;
      for (const term of searchTerms) {
        if (text.includes(term)) score++;
      }
      if (matcher === FIELD_MATCHERS.experience) {
        if (text.includes("fresher") || text.includes("0") || text.match(/0[\s-]*1/)) {
          score += 5;
        }
      }
      // Naukri notice period: prefer "Immediate" or "15 days"
      if (platform === "naukri" && getFieldSignature(el).includes("notice")) {
        if (text.includes("immediate") || text.includes("15 day")) score += 5;
      }
      if (score > bestScore) {
        bestScore = score;
        bestMatch = option;
      }
    }

    if (bestMatch && bestScore > 0) {
      el.value = bestMatch.value;
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    return false;
  }

  function highlightField(el) {
    el.style.outline = "2px solid #4caf50";
    el.style.outlineOffset = "-1px";
    el.style.transition = "outline 0.3s ease";
  }

  // Track fill details for summary
  const details = [];
  let filled = 0;
  let total = 0;

  // Step 1: Try platform-specific direct selectors first
  const directSelectors = PLATFORM_DIRECT[platform] || [];
  const directFilled = new Set();

  for (const entry of directSelectors) {
    if (!entry.value) continue;
    let found = false;
    for (const sel of entry.selectors) {
      try {
        const el = document.querySelector(sel);
        if (el && isVisible(el) && !el.disabled && !el.readOnly) {
          if (!el.value || el.value.trim() === "") {
            setNativeValue(el, entry.value);
            highlightField(el);
            filled++;
            directFilled.add(el);
            found = true;
            details.push({ field: entry.field, filled: true });
            break;
          }
        }
      } catch (e) { /* invalid selector, skip */ }
    }
    if (!found) {
      details.push({ field: entry.field, filled: false });
    }
  }

  // Step 2: Fall back to generic pattern matching for remaining fields
  const inputs = document.querySelectorAll("input, textarea, select");

  for (const el of inputs) {
    if (directFilled.has(el)) continue;
    if (!isVisible(el)) continue;
    if (el.disabled || el.readOnly) continue;

    const type = el.type?.toLowerCase();
    if (["hidden", "submit", "button", "reset", "checkbox", "radio", "file", "image"].includes(type)) {
      if (type === "file") {
        const sig = getFieldSignature(el);
        if (sig.includes("resume") || sig.includes("cv") || sig.includes("attachment")) {
          el.click();
        }
      }
      continue;
    }

    const signature = getFieldSignature(el);
    if (!signature) continue;

    total++;

    if (el.value && el.value.trim() !== "") continue;

    let matched = false;

    for (const [key, matcher] of Object.entries(FIELD_MATCHERS)) {
      if (!matcher.value) continue;
      if (!matchField(signature, matcher)) continue;

      if (el.tagName === "SELECT") {
        matched = handleSelect(el, matcher);
      } else {
        setNativeValue(el, matcher.value);
        matched = true;
      }

      if (matched) {
        highlightField(el);
        filled++;
        details.push({ field: key, filled: true });
        break;
      }
    }
  }

  return {
    filled,
    total: total + directSelectors.length,
    platformName: platformNames[platform] || platform,
    details
  };
}

// Init on open
init();
