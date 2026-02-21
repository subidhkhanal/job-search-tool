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
  skills: "Python, LangChain, RAG, FastAPI, OpenAI API, ChromaDB, Next.js, Agentic AI"
};

const FIELD_IDS = [
  "fullName", "email", "phone", "linkedin", "github",
  "portfolio", "location", "currentRole", "experience", "skills"
];

// DOM refs
const mainView = document.getElementById("main-view");
const settingsView = document.getElementById("settings-view");
const fillBtn = document.getElementById("fill-btn");
const settingsBtn = document.getElementById("settings-btn");
const backBtn = document.getElementById("back-btn");
const settingsForm = document.getElementById("settings-form");
const statusEl = document.getElementById("status");
const saveStatusEl = document.getElementById("save-status");
const displayName = document.getElementById("display-name");
const displayEmail = document.getElementById("display-email");

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

// Initialize popup
async function init() {
  const profile = await loadProfile();
  displayName.textContent = profile.fullName || "Set up your profile";
  displayEmail.textContent = profile.email || "Click settings to get started";
}

// Fill form button
fillBtn.addEventListener("click", async () => {
  const profile = await loadProfile();

  fillBtn.disabled = true;
  fillBtn.textContent = "Filling...";

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: fillFormFields,
      args: [profile]
    });

    const result = results[0]?.result;
    if (result) {
      showStatus(statusEl, `Filled ${result.filled}/${result.total} fields`, "success");
    } else {
      showStatus(statusEl, "No form fields found on this page", "info");
    }
  } catch (err) {
    showStatus(statusEl, "Cannot fill on this page (restricted)", "error");
  }

  fillBtn.disabled = false;
  fillBtn.textContent = "Fill Form";
});

// Settings navigation
settingsBtn.addEventListener("click", async () => {
  const profile = await loadProfile();
  FIELD_IDS.forEach((id) => {
    document.getElementById(id).value = profile[id] || "";
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
    profile[id] = document.getElementById(id).value.trim();
  });
  await saveProfile(profile);
  showStatus(saveStatusEl, "Saved!", "success");
});

// The function injected into the page
function fillFormFields(profile) {
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

    // Also check associated label
    const labelEl = el.labels?.[0] || (el.id && document.querySelector(`label[for="${el.id}"]`));
    if (labelEl) {
      attrs.push(labelEl.textContent);
    }

    return attrs.filter(Boolean).map(s => s.toLowerCase().trim()).join(" ");
  }

  function matchField(signature, matcher) {
    // Check excludes first
    for (const excl of matcher.excludePatterns) {
      if (signature.includes(excl)) return false;
    }
    // Check includes
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

    // Try exact match first, then partial
    let bestMatch = null;
    let bestScore = 0;

    for (const option of options) {
      if (option.disabled || option.value === "") continue;
      const text = (option.text + " " + option.value).toLowerCase();

      let score = 0;
      for (const term of searchTerms) {
        if (text.includes(term)) score++;
      }

      // Special handling for experience dropdowns
      if (matcher === FIELD_MATCHERS.experience) {
        if (text.includes("fresher") || text.includes("0") || text.match(/0[\s-]*1/)) {
          score += 5;
        }
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

  // Gather all inputs, textareas, and selects
  const inputs = document.querySelectorAll("input, textarea, select");
  let filled = 0;
  let total = 0;

  for (const el of inputs) {
    if (!isVisible(el)) continue;
    if (el.disabled || el.readOnly) continue;

    const type = el.type?.toLowerCase();
    if (["hidden", "submit", "button", "reset", "checkbox", "radio", "file", "image"].includes(type)) {
      // For file inputs, trigger the picker
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

    // Skip if already has content
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
        break;
      }
    }
  }

  return { filled, total };
}

// Init on open
init();
