import { useEffect, useMemo, useState } from "react";
import "./styles.css";

const districts = [
  "Bugesera", "Burera", "Gakenke", "Gasabo", "Gatsibo", "Gicumbi",
  "Gisagara", "Huye", "Kamonyi", "Karongi", "Kayonza", "Kicukiro",
  "Kirehe", "Muhanga", "Musanze", "Ngoma", "Ngororero", "Nyabihu",
  "Nyagatare", "Nyamagabe", "Nyamasheke", "Nyanza", "Nyarugenge",
  "Nyaruguru", "Rubavu", "Ruhango", "Rulindo", "Rusizi", "Rutsiro",
  "Rwamagana"
];

const seasons = {
  A: "Sep 2024 – Feb 2025",
  B: "Mar – Jun 2025",
  C: "Jul – Sep 2025"
};

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const split = (line) => {
    const cells = [];
    let value = "";
    let quoted = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"' && line[i + 1] === '"' && quoted) {
        value += '"'; i++;
      } else if (ch === '"') quoted = !quoted;
      else if (ch === "," && !quoted) {
        cells.push(value.trim()); value = "";
      } else value += ch;
    }
    cells.push(value.trim());
    return cells;
  };
  const headers = split(lines[0]);
  return lines.slice(1).filter(Boolean).map((line) => {
    const values = split(line);
    return Object.fromEntries(headers.map((h, i) => [h, values[i] ?? ""]));
  });
}

const number = (v) => {
  if (v == null || String(v).trim() === "") return null;
  const n = Number(String(v).replace(/,/g, ""));
  return Number.isFinite(n) ? n : null;
};
const fmt = (n) => new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1
}).format(n);

function App() {
  const [showWelcomeIntro, setShowWelcomeIntro] = useState(true);

  useEffect(() => {
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    if (reducedMotion.matches) {
      setShowWelcomeIntro(false);
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setShowWelcomeIntro(false);
    }, 3700);

    return () => window.clearTimeout(timer);
  }, []);

  const [page, setPage] = useState("home");
  const [analysisMenuOpen, setAnalysisMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [language, setLanguage] = useState("rw");
  const rw = language === "rw";
  const t = (en, rwText) => rw ? rwText : en;

  // MENYA NEZA AI question workspace
  const [askDraft, setAskDraft] = useState("");
  const [askResult, setAskResult] = useState(null);
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState("");
  const [askHistory, setAskHistory] = useState([]);
  const fallbackAskSuggestions = [
    {
      icon: "↗",
      en: "What are the NST2 maize production targets?",
      rwText: "Ni iyihe ntego ya NST2 ku musaruro w'ibigori?"
    },
    {
      icon: "⌖",
      en: "How much maize did Huye report in Season B 2025?",
      rwText: "Huye yatangaje toni zingahe z'ibigori mu gihembwe B cya 2025?"
    },
    {
      icon: "◷",
      en: "Compare beans production across seasons in 2025",
      rwText: "Gereranya umusaruro w'ibishyimbo mu bihembwe bya 2025"
    },
    {
      icon: "◎",
      en: "What are the data quality limitations?",
      rwText: "Ni izihe mbogamizi z'ubwiza bw'amakuru?"
    }
  ];


  // ASK_BANK_FRONTEND_INTEGRATION
  const [askSuggestions, setAskSuggestions] = useState(fallbackAskSuggestions);

  useEffect(() => {
    let cancelled = false;
    const language = rw ? "rw" : "en";
    const terms = rw
      ? ["ibigori", "ibishyimbo", "imyumbati", "ibirayi"]
      : ["maize", "beans", "cassava", "potatoes"];
    const icons = ["↗", "⌖", "◷", "◎"];

    const loadQuestionBankSuggestions = async () => {
      try {
        const results = await Promise.all(
          terms.map(async (term) => {
            const params = new URLSearchParams({
              q: term,
              language,
              limit: "1",
            });
            const response = await fetch(
              `/api/v1/ask/knowledge/questions?${params.toString()}`
            );

            if (!response.ok) return null;

            const data = await response.json();
            return data.questions?.[0] ?? null;
          })
        );

        if (cancelled) return;

        const questions = results.filter(Boolean).map((item, index) => ({
          icon: icons[index],
          en: item.question,
          rwText: item.question,
          bankId: item.id,
        }));

        if (questions.length > 0) {
          setAskSuggestions(questions);
        } else {
          setAskSuggestions(fallbackAskSuggestions);
        }
      } catch {
        if (!cancelled) {
          setAskSuggestions(fallbackAskSuggestions);
        }
      }
    };

    loadQuestionBankSuggestions();

    return () => {
      cancelled = true;
    };
  }, [rw]);

  const submitAsk = async (questionOverride) => {
    const question = String(questionOverride ?? askDraft).trim();
    if (!question || askLoading) return;

    setAskDraft(question);
    setAskLoading(true);
    setAskError("");
    setAskResult(null);

    try {
      const response = await fetch("/api/v1/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          language,
          conversation: askHistory.slice(-6).map((item) => ({
            question: item.question,
            result: item.result,
          })),
        })
      });

      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error(
          rw
            ? "Seriveri yagaruye igisubizo kitumvikana. Ongera ugerageze."
            : "The server returned an unreadable response. Please try again."
        );
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
          (rw ? "Ikibazo nticyashoboye gusubizwa." : "The question could not be processed.")
        );
      }

      setAskResult(data);
      setAskHistory(previous => [
        ...previous,
        { question, result: data, id: `${Date.now()}-${previous.length}` }
      ]);
    } catch (error) {
      setAskError(
        error?.message ||
        (rw
          ? "Ntibishobotse kugera kuri seriveri. Reba niba backend iri gukora."
          : "Could not reach the assistant. Check that the backend is running.")
      );
    } finally {
      setAskLoading(false);
    }
  };

  const renderAskValue = (value) => {
    if (value == null || value === "") return null;
    if (typeof value === "string" || typeof value === "number") return String(value);
    return JSON.stringify(value, null, 2);
  };


  // Amazina y'Ikinyarwanda; amazina y'umwimerere ya NISR ntahindurwa.
  const cropNamesRw = {
    "Banana": "Ibitoki",
    "Banana for beer": "Ibitoki byo gukora inzoga",
    "Beans": "Ibishyimbo",
    "Bush bean": "Ibishyimbo by'ibihuru",
    "Cassava": "Imyumbati",
    "Climbing bean": "Ibishyimbo birandaranda",
    "Cooking banana": "Ibitoki byo guteka",
    "Dessert banana": "Ibitoki byo kurya",
    "Fodder crops": "Ibihingwa bigaburirwa amatungo",
    "Fruits": "Imbuto",
    "Ground nuts": "Ubunyobwa",
    "Groundnut": "Ubunyobwa",
    "Irish potatoes": "Ibirayi",
    "Maize": "Ibigori",
    "Other cereals": "Ibindi binyampeke",
    "Other crops": "Ibindi bihingwa",
    "Paddy rice": "Umuceri utaratonorwa",
    "Pea": "Ishaza",
    "Peas": "Amashaza",
    "Sorghum": "Amasaka",
    "Soya bean": "Soya",
    "Soya beans": "Soya",
    "Sweet potatoes": "Ibijumba",
    "Vegetables": "Imboga",
    "Wheat": "Ingano",
    "Yams & Taro": "Ibikoro na taro"
  };

  const displayCropName = (name) =>
    rw ? (cropNamesRw[name] || name) : name;

  const [district, setDistrict] = useState("Huye");
  const [season, setSeason] = useState("B");
  const [records, setRecords] = useState([]);
  const [checks, setChecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [originCrop, setOriginCrop] = useState("Maize");
  const [originSeason, setOriginSeason] = useState("B");
  const [origins, setOrigins] = useState(null);
  const [originsLoading, setOriginsLoading] = useState(false);
  const [originsError, setOriginsError] = useState("");
  const [seasonalCrop, setSeasonalCrop] = useState("Beans");
  const [seasonalData, setSeasonalData] = useState(null);
  const [seasonalLoading, setSeasonalLoading] = useState(false);
  const [seasonalError, setSeasonalError] = useState("");

  const [qualitySeason, setQualitySeason] = useState("all");
  const [qualityCrop, setQualityCrop] = useState("all");
  const [qualityStatus, setQualityStatus] = useState("all");
  const [qualityDetailOpen, setQualityDetailOpen] = useState(null);
  const [qualityDistrictSearch, setQualityDistrictSearch] = useState({});
  const [qualityDistrictSearchIndex, setQualityDistrictSearchIndex] = useState({});
  const [qualityDetails, setQualityDetails] = useState({});
  const [qualityDetailLoading, setQualityDetailLoading] = useState({});
  const [qualityDetailErrors, setQualityDetailErrors] = useState({});
  const [qualityCitationStatus, setQualityCitationStatus] = useState("");

  // Market Intelligence has its own state and data request.
  const [intelCrop, setIntelCrop] = useState("Maize");
  const [intelSeason, setIntelSeason] = useState("B");
  const [intelReport, setIntelReport] = useState(null);
  const [intelLoading, setIntelLoading] = useState(false);
  const [intelError, setIntelError] = useState("");

  // TangaBid price summaries remain separate from NISR production evidence.
  const [priceData, setPriceData] = useState(null);
  const [priceLoading, setPriceLoading] = useState(false);
  const [priceError, setPriceError] = useState("");
  const [priceOffset, setPriceOffset] = useState(0);
  const [priceRefresh, setPriceRefresh] = useState(0);
  const [trendData, setTrendData] = useState(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState("");
  const [priceFilters, setPriceFilters] = useState({
    product: "",
    month: "",
    region: "",
    location: "",
    unit: "",
  });
  const pricePageSize = 25;


  const qualitySeasons = useMemo(
    () => [...new Set(checks.map(r => r.season).filter(Boolean))].sort(),
    [checks]
  );
  const qualityCrops = useMemo(
    () => [...new Set(checks.map(r => r.crop).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b)),
    [checks]
  );
  const qualityStatuses = useMemo(
    () => [...new Set(checks.map(r => r.validation_status || "UNKNOWN"))].sort(),
    [checks]
  );
  const filteredChecks = useMemo(
    () => checks.filter(r =>
      (qualitySeason === "all" || r.season === qualitySeason) &&
      (qualityCrop === "all" || r.crop === qualityCrop) &&
      (qualityStatus === "all" ||
        (r.validation_status || "UNKNOWN") === qualityStatus)
    ),
    [checks, qualitySeason, qualityCrop, qualityStatus]
  );

  const toggleQualityDetails = async (record, forceReload = false) => {
    const key = `${record.year}-${record.season}-${record.crop}`;

    if (qualityDetailOpen === key && !forceReload) {
      setQualityDetailOpen(null);
      return;
    }

    setQualityDetailOpen(key);

    if (qualityDetails[key] && !forceReload) return;

    setQualityDetailLoading(previous => ({
      ...previous,
      [key]: true
    }));
    setQualityDetailErrors(previous => ({ ...previous, [key]: "" }));

    try {
      const params = new URLSearchParams({
        crop: record.crop,
        season: String(record.season),
        year: String(record.year)
      });
      const response = await fetch(
        `/api/v1/supply/origins?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error("DISTRICT_DETAILS_LOAD_FAILED");
      }

      const data = await response.json();
      setQualityDetails(previous => ({ ...previous, [key]: data }));
    } catch {
      setQualityDetailErrors(previous => ({
        ...previous,
        [key]: "DISTRICT_DETAILS_LOAD_FAILED"
      }));
    } finally {
      setQualityDetailLoading(previous => {
        const next = { ...previous };
        delete next[key];
        return next;
      });
    }
  };



  useEffect(() => {
    if (page !== "intelligence") return undefined;

    const controller = new AbortController();

    async function loadIntelligence() {
      setIntelLoading(true);
      setIntelError("");

      try {
        const params = new URLSearchParams({
          crop: intelCrop,
          season: intelSeason,
          year: "2025",
          district
        });

        const response = await fetch(
          `/api/v1/intelligence/supply-price?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("INTELLIGENCE_LOAD_FAILED");
        }

        const data = await response.json();
        if (!controller.signal.aborted) setIntelReport(data);
      } catch (error) {
        if (error.name !== "AbortError" && !controller.signal.aborted) {
          setIntelError("INTELLIGENCE_LOAD_FAILED");
        }
      } finally {
        if (!controller.signal.aborted) setIntelLoading(false);
      }
    }

    loadIntelligence();
    return () => controller.abort();
  }, [page, intelCrop, intelSeason, district]);

  useEffect(() => {
    if (page !== "intelligence") return undefined;

    const controller = new AbortController();

    async function loadPriceTrends() {
      setPriceLoading(true);
      setPriceError("");

      try {
        const params = new URLSearchParams({
          limit: String(pricePageSize),
          offset: String(priceOffset),
        });

        Object.entries(priceFilters).forEach(([key, value]) => {
          if (value) params.set(key, value);
        });

        const response = await fetch(
          `/api/v1/market-prices/trends?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("PRICE_TRENDS_LOAD_FAILED");
        }

        const data = await response.json();
        if (!controller.signal.aborted) setPriceData(data);
      } catch (error) {
        if (error.name !== "AbortError" && !controller.signal.aborted) {
          setPriceError("PRICE_TRENDS_LOAD_FAILED");
          setPriceData(null);
        }
      } finally {
        if (!controller.signal.aborted) setPriceLoading(false);
      }
    }

    loadPriceTrends();
    return () => controller.abort();
  }, [page, priceFilters, priceOffset, priceRefresh]);

  useEffect(() => {
    if (
      page !== "intelligence" ||
      !priceFilters.product ||
      !priceFilters.unit ||
      !priceFilters.location
    ) {
      setTrendData(null);
      setTrendError("");
      setTrendLoading(false);
      return;
    }

    const controller = new AbortController();

    async function loadMonthlyTrend() {
      setTrendLoading(true);
      setTrendError("");

      try {
        const params = new URLSearchParams({
          product: priceFilters.product,
          unit: priceFilters.unit,
          location: priceFilters.location,
          limit: "1000",
          offset: "0",
        });

        if (priceFilters.region) {
          params.set("region", priceFilters.region);
        }

        const response = await fetch(
          `/api/v1/market-prices/trends?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error(`Trend request failed: ${response.status}`);
        }

        const result = await response.json();

        if (result.total_matching_records > result.records.length) {
          throw new Error("The full trend history exceeds the chart request limit.");
        }

        setTrendData(result);
      } catch (error) {
        if (!controller.signal.aborted && error.name !== "AbortError") {
          setTrendError("TREND_DATA_LOAD_FAILED");
          setTrendData(null);
        }
      } finally {
        if (!controller.signal.aborted) {
          setTrendLoading(false);
        }
      }
    }

    loadMonthlyTrend();
    return () => controller.abort();
  }, [
    page,
    priceFilters.product,
    priceFilters.unit,
    priceFilters.location,
    priceFilters.region,
    priceRefresh,
  ]);



  const errorMessage = (code) => {
    const messages = {
      CROP_DATA_LOAD_FAILED: [
        "Crop data could not be loaded from the API.",
        "Amakuru y'umusaruro w'ibihingwa ntiyabashije kuboneka."
      ],
      REMAINING_CROP_DATA_LOAD_FAILED: [
        "The remaining crop data could not be loaded.",
        "Andi makuru asigaye y'umusaruro ntiyabashije kuboneka."
      ],
      DATA_QUALITY_LOAD_FAILED: [
        "Data-quality checks could not be loaded from the API.",
        "Igenzura ry'ubwiza bw'amakuru ntiryabashije kuboneka."
      ],
      UNEXPECTED_ERROR: [
        "An unexpected error occurred.",
        "Habaye ikibazo kitari cyitezwe."
      ]
    };

    const message = messages[code] || messages.UNEXPECTED_ERROR;
    return rw ? message[1] : message[0];
  };

  useEffect(() => {
    let cancelled = false;

    async function loadApiData() {
      try {
        const firstResponse = await fetch("/api/v1/production?limit=1000&offset=0");
        if (!firstResponse.ok) {
          throw new Error("CROP_DATA_LOAD_FAILED");
        }

        const firstPage = await firstResponse.json();
        const allRecords = [...firstPage.records];
        const totalRecords = firstPage.total_matching_records;

        for (let offset = allRecords.length; offset < totalRecords; offset += 1000) {
          const response = await fetch(
            `/api/v1/production?limit=1000&offset=${offset}`
          );
          if (!response.ok) {
            throw new Error("REMAINING_CROP_DATA_LOAD_FAILED");
          }
          const pageData = await response.json();
          allRecords.push(...pageData.records);
        }

        const qualityResponse = await fetch("/api/v1/data-quality");
        if (!qualityResponse.ok) {
          throw new Error("DATA_QUALITY_LOAD_FAILED");
        }

        const qualityData = await qualityResponse.json();

        if (!cancelled) {
          setRecords(allRecords);
          setChecks(qualityData.records ?? []);
          setLoading(false);
        }
      } catch (e) {
        if (!cancelled) {
          const knownErrors = [
            "CROP_DATA_LOAD_FAILED",
            "REMAINING_CROP_DATA_LOAD_FAILED",
            "DATA_QUALITY_LOAD_FAILED"
          ];
          setError(
            e instanceof Error && knownErrors.includes(e.message)
              ? e.message
              : "UNEXPECTED_ERROR"
          );
          setLoading(false);
        }
      }
    }

    loadApiData();

    return () => {
      cancelled = true;
    };
  }, []);

  const originCrops = useMemo(
    () => [...new Set(records.map(r => r.crop).filter(Boolean))].sort(),
    [records]
  );

  useEffect(() => {
    if (page !== "origins") return undefined;

    const controller = new AbortController();

    async function loadOrigins() {
      setOriginsLoading(true);
      setOriginsError("");

      try {
        const params = new URLSearchParams({
          crop: originCrop,
          season: originSeason,
          year: "2025"
        });
        const response = await fetch(
          `/api/v1/supply/origins?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("ORIGINS_LOAD_FAILED");
        }

        const data = await response.json();
        if (!controller.signal.aborted) setOrigins(data);
      } catch (e) {
        if (!controller.signal.aborted) {
          setOriginsError(
            e instanceof Error && e.name === "AbortError"
              ? ""
              : "ORIGINS_LOAD_FAILED"
          );
          setOrigins(null);
        }
      } finally {
        if (!controller.signal.aborted) setOriginsLoading(false);
      }
    }

    loadOrigins();
    return () => controller.abort();
  }, [page, originCrop, originSeason]);

  useEffect(() => {
    if (page !== "seasonal") return undefined;

    const controller = new AbortController();

    async function loadSeasonalComparison() {
      setSeasonalLoading(true);
      setSeasonalError("");

      try {
        const params = new URLSearchParams({
          crop: seasonalCrop,
          year: "2025"
        });
        const response = await fetch(
          `/api/v1/production/seasonal-comparison?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("SEASONAL_COMPARISON_LOAD_FAILED");
        }

        const data = await response.json();
        if (!controller.signal.aborted) setSeasonalData(data);
      } catch (e) {
        if (!controller.signal.aborted) {
          setSeasonalError(
            e instanceof Error && e.name === "AbortError"
              ? ""
              : "SEASONAL_COMPARISON_LOAD_FAILED"
          );
          setSeasonalData(null);
        }
      } finally {
        if (!controller.signal.aborted) setSeasonalLoading(false);
      }
    }

    loadSeasonalComparison();
    return () => controller.abort();
  }, [page, seasonalCrop]);

  const area = useMemo(() => records.filter(r =>
    r.district?.toLowerCase() === district.toLowerCase() &&
    r.season === season && Number(r.year) === 2025
  ), [records, district, season]);

  const crops = useMemo(() => area.map(r => ({
    name: r.crop,
    value: number(r.production_mt),
    reported: r.source_value_status === "reported"
  })).filter(r => r.value !== null && r.reported).sort((a, b) => b.value - a.value), [area]);

  const reported = area.filter(r => r.source_value_status === "reported").length;
  const missing = area.length - reported;
  const max = Math.max(...crops.map(c => c.value), 1);
  const completeChecks = checks.filter(c =>
    c.validation_status !== "INCOMPLETE_DISTRICT_DATA"
  ).length;

  // Reusable explanations that follow the selected interface language.
  const ExplainThis = ({ en, rwText }) => (
    <details className="explain-details">
      <summary>{t("What does this mean?", "Bisobanuye iki?")}</summary>
      <p>{rw ? rwText : en}</p>
    </details>
  );

  const navigate = (next) => {
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const askEvidence = Array.isArray(askResult?.evidence)
    ? askResult.evidence
    : [];

  return (
    <div className="app-shell">
      {showWelcomeIntro && (
        <div
          className="welcome-intro-overlay"
          role="status"
          aria-label="Welcome to MENYA NEZA AI"
        >
          <div className="welcome-intro-content">
            <div className="welcome-intro-emblem" aria-hidden="true">
              <span className="welcome-intro-orbit" />
              <span className="welcome-intro-orbit welcome-intro-orbit-second" />
              <span className="welcome-intro-logo">
                <img src="/menya-neza-ai-logo.png" alt="" />
              </span>
              <span className="welcome-intro-emblem-dot" />
            </div>

            <div className="welcome-intro-copy">
              <p className="welcome-intro-kicker">WELCOME TO</p>
              <h1>MENYA NEZA <span>AI</span></h1>
              <div className="welcome-intro-rule" aria-hidden="true">
                <span />
              </div>
              <p className="welcome-intro-tagline">FROM DATA TO EARLY ACTION</p>
            </div>
          </div>
          <div className="welcome-intro-footer" aria-hidden="true">
            <span>RWANDA</span>
            <span className="welcome-intro-footer-dot" />
            <span>AGRICULTURE · FOOD · PREPAREDNESS</span>
          </div>
        </div>
      )}
      <header className="topbar" id="top">
        <button className="brand" onClick={() => navigate("home")}>
          <span className="brand-mark">
                <img src="/menya-neza-ai-logo.png" alt="" />
              </span>
          <span className="brand-copy">
            <strong>MENYA NEZA <i>AI</i></strong>
            <small>{t("FROM DATA TO EARLY ACTION", "DUHERA KU MIBARE TUGAFASHA ABANTU KWITEGURA")}</small>
          </span>
        </button>

        <nav
          className={`desktop-nav${mobileMenuOpen ? " mobile-open" : ""}`}
          aria-label="Main navigation"
        >
          <button
            className={page === "home" ? "nav-link active" : "nav-link"}
            onClick={() => {
              navigate("home");
              setMobileMenuOpen(false);
              setAnalysisMenuOpen(false);
            }}
          >
            {t("Home", "Ahabanza")}
          </button>

          <button
            className={page === "area" ? "nav-link active" : "nav-link"}
            onClick={() => {
              navigate("area");
              setMobileMenuOpen(false);
              setAnalysisMenuOpen(false);
            }}
          >
            {t("Check My Area", "Menya Akarere")}
          </button>

          <div className="nav-dropdown">
            <button
              type="button"
              className={
                ["insights", "origins", "seasonal", "quality", "intelligence"].includes(page)
                  ? "nav-link active dropdown-trigger"
                  : "nav-link dropdown-trigger"
              }
              aria-expanded={analysisMenuOpen}
              onClick={() => setAnalysisMenuOpen(open => !open)}
            >
              {t("Analysis", "Ubusesenguzi")}
              <span aria-hidden="true">{analysisMenuOpen ? "⌃" : "⌄"}</span>
            </button>

            <div
              className={`nav-dropdown-menu${analysisMenuOpen ? " open" : ""}`}
            >
              <button onClick={() => {
                navigate("insights");
                setAnalysisMenuOpen(false);
                setMobileMenuOpen(false);
              }}>
                {t("Insights", "Ibyo imibare itugaragariza")}
              </button>
              <button onClick={() => {
                navigate("origins");
                setAnalysisMenuOpen(false);
                setMobileMenuOpen(false);
              }}>
                {t("Supply Origins", "Aho umusaruro ukomoka")}
              </button>
              <button onClick={() => {
                navigate("seasonal");
                setAnalysisMenuOpen(false);
                setMobileMenuOpen(false);
              }}>
                {t("Seasonal Comparison", "Kugereranya ibihembwe")}
              </button>
              <button onClick={() => {
                navigate("intelligence");
                setAnalysisMenuOpen(false);
                setMobileMenuOpen(false);
              }}>
                {t("Market Intelligence", "Ubusesenguzi bw'amasoko")}
              </button>
              <button onClick={() => {
                navigate("quality");
                setAnalysisMenuOpen(false);
                setMobileMenuOpen(false);
              }}>
                {t("Data Quality & Sources", "Ubwiza n'inkomoko by'amakuru")}
              </button>
            </div>
          </div>

          <button
            className={page === "about" ? "nav-link active" : "nav-link"}
            onClick={() => {
              navigate("about");
              setMobileMenuOpen(false);
              setAnalysisMenuOpen(false);
            }}
          >
            {t("About", "Umushinga")}
          </button>
        </nav>

        <div className="header-actions">
          <button
            type="button"
            className="mobile-menu-toggle"
            aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={mobileMenuOpen}
            onClick={() => {
              setMobileMenuOpen(open => !open);
              setAnalysisMenuOpen(false);
            }}
          >
            <span>{mobileMenuOpen ? "✕" : "☰"}</span>
            <span className="mobile-menu-label">
              {t("Menu", "Ibikubiyemo")}
            </span>
          </button>
          <div className="language-switch" role="group" aria-label="Language / Ururimi">
            <button type="button" className={!rw ? "language-option selected" : "language-option"}
              aria-pressed={!rw} onClick={() => setLanguage("en")}>EN</button>
            <button type="button" className={rw ? "language-option selected" : "language-option"}
              aria-pressed={rw} onClick={() => setLanguage("rw")}>RW</button>
          </div>
          <button className="menu-cta" onClick={() => navigate("area")}>
            {t("Explore", "Tangira")} <span>↗</span>
          </button>
        </div>
      </header>

      {page === "home" && (
        <main className="mn-home">
          <section className="home-hero">
            <div className="home-ai-layout">
              <div className="home-copy">
                <div className="eyebrow">
                  <span className="eyebrow-dot" />
                  {t("RWANDA AGRICULTURAL INTELLIGENCE", "UBWENGE KU BUHINZI BW'U RWANDA")}
                </div>

                <div className="home-brandline">
                  <img
                    className="home-hero-logo"
                    src="/menya-neza-ai-logo.png"
                    alt=""
                    aria-hidden="true"
                  />
                  <span className="home-brand-name">
                    MENYA NEZA <span className="home-brand-ai">AI</span>
                  </span>
                </div>

                <h1>
                  {t("Understand the harvest.", "Menya umusaruro.")}
                  <br />
                  <em>{t("Prepare for tomorrow.", "Witegure ejo hazaza.")}</em>
                </h1>

                <p className="home-description">
                  {t(
                    "Explore Rwanda's crop-production data, compare agricultural seasons, and review available market-price information. Understand what the evidence shows, where information is missing, and what that means for decisions.",
                    "SOBANUKIRWA N'UMUSARURO W'IBIHINGWA MU RWANDA, UGERERANYE IBIHEMBWE BY'UBUHINZI, KANDI UREBE AMAKURU ABONEKA KU BICIRO BYO KU MASOKO. MENYA ICYO IMIBARE IGARAGAZA, AMAKURU ABURA N'IMBOGAMIZI ZIHARI KUGIRA NGO UFATE IBYEMEZO BISHINGIYE KU MAKURU."
                  )}
                </p>

                <div className="hero-buttons">
                  <button className="primary-button" onClick={() => navigate("area")}>
                    {t("Explore crop production", "Menya umusaruro")} <span>↗</span>
                  </button>
                  <button className="text-button" onClick={() => navigate("intelligence")}>
                    {t("Explore the evidence", "Sobanukirwa n'amakuru")} <span>→</span>
                  </button>
                </div>

                <div className="home-trust">
                  <span className="trust-icon">✓</span>
                  <span>
                    <b>{t("Clear evidence. Better decisions.", "Amakuru asobanutse, ibyemezo byiza")}</b>
                    <small>
                      {t(
                        "Historical data is clearly labelled. Missing information stays unknown. No invented live warnings.",
                        "Amakuru yo mu bihe byashize aragaragazwa. Amakuru abura ntahindurwa zeru. Nta miburo y'ako kanya ihimbwa."
                      )}
                    </small>
                  </span>
                </div>
              </div>


            </div>

            <div className="home-bottomline">
              <span>{t("DATA", "AMAKURU")}</span><i />
              <span>{t("AGRICULTURE", "UBUHINZI")}</span><i />
              <span>{t("FOOD SYSTEMS", "URUNANA RW'IBIRIBWA")}</span><i />
              <span>{t("PREPAREDNESS", "KWITEGURA")}</span>
            </div>
          </section>


          <section className="home-assistant-section" aria-label="MENYA NEZA AI assistant">
            <div className="home-assistant-intro">
              <span className="home-assistant-spark" aria-hidden="true">✳</span>
              <span>{t("EVIDENCE-GROUNDED AGRICULTURAL INTELLIGENCE", "UBWENGE BW'UBUHINZI BUSHINGIYE KU BIMENYETSO")}</span>
            </div>

            <div className="mn-ai-workspace">
              <main className="mn-ai-conversation">
                <header className="mn-ai-header">
                  <div className="mn-ai-identity">
                    <div className="home-ai-logo-wrap mn-ai-logo">
                      <img src="/menya-neza-ai-logo.png" alt="MENYA NEZA AI logo" />
                    </div>
                    <div>
                      <span className="mn-ai-eyebrow">{t("RWANDA AGRICULTURE DATA", "AMAKURU Y'UBUHINZI MU RWANDA")}</span>
                      <h2>{t("Ask MENYA NEZA", "Baza MENYA NEZA")}</h2>
                      <p>{t("Ask a question. Get an answer grounded in available evidence.", "Baza ikibazo. Uhabwe igisubizo gishingiye ku bimenyetso biboneka.")}</p>
                    </div>
                  </div>
                  <span className="mn-ai-status">
                    <i aria-hidden="true" />
                    {t("DATA-BASED", "ISHINGIYE KU MAKURU")}
                  </span>
                </header>

                <div className="mn-ai-message-area" aria-live="polite" aria-busy={askLoading}>
                  {!askResult && !askLoading && !askError && (
                    <div className="mn-ai-empty-state">
                      <div className="mn-ai-assistant-mark" aria-hidden="true">✳</div>
                      <div className="mn-ai-welcome">
                        <span className="mn-ai-welcome-hello">Hello 👋</span>
                        <h3>{t("How can we help today?", "Tugufashe gute nonaha?")}</h3>
                        <p>{t("Choose a topic or ask your own question.", "Hitamo ingingo cyangwa wandike ikibazo cyawe.")}</p>
                      </div>
                    </div>
                  )}

                  {askLoading && (
                    <div className="mn-ai-loading" role="status">
                      <span className="mn-ai-spinner" />
                      <div>
                        <strong>{t("Checking the available evidence…", "Harimo kugenzurwa ibimenyetso biboneka…")}</strong>
                        <p>{t("Reviewing the data before preparing an answer.", "Harimo gusuzuma amakuru mbere yo gutegura igisubizo.")}</p>
                      </div>
                    </div>
                  )}

                  {askError && (
                    <div className="mn-ai-error" role="alert">
                      <strong>{t("The assistant could not complete this request", "Umufasha ntiyashoboye gusubiza iki kibazo")}</strong>
                      <p>{askError}</p>
                      <button type="button" onClick={() => submitAsk(askDraft)}>
                        {t("Try again", "Ongera ugerageze")}
                      </button>
                    </div>
                  )}

                  {askResult && (
                    <article className="mn-ai-answer">
                      <div className="mn-ai-answer-heading">
                        <span className="mn-ai-answer-icon" aria-hidden="true">✳</span>
                        <div>
                          <span className="mn-ai-eyebrow">{t("MENYA NEZA RESPONSE", "IGISUBIZO CYA MENYA NEZA")}</span>
                          <strong>{t("Evidence-based answer", "Igisubizo gishingiye ku bimenyetso")}</strong>
                        </div>
                        <span className={`mn-ai-result-status mn-ai-result-${String(askResult.status || "result").replace(/[^a-z0-9_-]/gi, "")}`}>
                          {String(askResult.status || t("Response", "Igisubizo")).replaceAll("_", " ")}
                        </span>
                      </div>

                      <div className="mn-ai-answer-text">
                        {String(askResult.answer || t("No answer text was returned.", "Nta gisubizo cy'inyandiko cyagaruwe."))
                          .split("\n")
                          .map((line, index) => (
                            <p key={`${index}-${line.slice(0, 20)}`}>{line || "\u00a0"}</p>
                          ))}
                      </div>

                      {askResult.ai_explanation && (
                        <div className="mn-ai-detail mn-ai-ai-explanation">
                          <span className="mn-ai-detail-label">
                            {t("OPTIONAL AI EXPLANATION", "IBISOBANURO BYONGEWE NA AI")}
                          </span>
                          <div className="mn-ai-answer-text">
                            {String(askResult.ai_explanation)
                              .split("\n")
                              .map((line, index) => (
                                <p key={`ai-${index}-${line.slice(0, 20)}`}>
                                  {line || "\u00a0"}
                                </p>
                              ))}
                          </div>
                          <p>
                            {t(
                              "AI-generated explanation based on the answer and evidence above; the verified answer remains the source of truth.",
                              "Ibisobanuro byakozwe na AI hashingiwe ku gisubizo n'ibimenyetso biri hejuru; igisubizo cyagenzuwe ni cyo kigenderwaho."
                            )}
                          </p>
                        </div>
                      )}

                      {askResult.source && (
                        <div className="mn-ai-detail">
                          <span className="mn-ai-detail-label">{t("SOURCE", "INKOMOKO")}</span>
                          <p>{renderAskValue(askResult.source)}</p>
                        </div>
                      )}

                      {askResult.source_note && (
                        <div className="mn-ai-detail">
                          <span className="mn-ai-detail-label">{t("SOURCE NOTE", "ICYITONDERWA KU Nkomoko")}</span>
                          <p>{renderAskValue(askResult.source_note)}</p>
                        </div>
                      )}

                      {askEvidence.length > 0 && (
                        <details className="mn-ai-evidence" open>
                          <summary>{t(`View supporting evidence (${askEvidence.length})`, `Reba ibimenyetso bishyigikira igisubizo (${askEvidence.length})`)}</summary>
                          <div className="mn-ai-evidence-grid">
                            {askEvidence.map((item, index) => {
                              const referenceIndicators =
                                item?.nst2_reference_indicators;

                              const fields = [
                                ["district", t("District", "Akarere")],
                                ["crop", t("Crop", "Igihingwa")],
                                ["season", t("Season", "Igihembwe")],
                                ["year", t("Year", "Umwaka")],
                                ["production_mt", t("Reported production", "Umusaruro watangajwe")],
                                ["source_table", t("Source table", "Imbonerahamwe")],
                                ["source_page", t("Page", "Urupapuro")],
                                ["value_status", t("Record status", "Imiterere y'inyandiko")],
                              ];

                              const hasBasicFacts = fields.some(
                                ([key]) => item?.[key] != null && item[key] !== ""
                              );

                              return (
                                <article className="mn-ai-evidence-card" key={index}>
                                  {referenceIndicators ? (
                                    <>
                                      <div className="mn-ai-evidence-card-heading">
                                        <span className="mn-ai-evidence-symbol">◎</span>
                                        <div>
                                          <span className="mn-ai-detail-label">
                                            {t("POLICY REFERENCE", "IBIPIMO NGENDERWAHO")}
                                          </span>
                                          <h4>
                                            {rw ? displayCropName(item.crop) : item.crop}
                                          </h4>
                                        </div>
                                      </div>

                                      <div className="mn-ai-target-list">
                                        {Object.entries(referenceIndicators).map(
                                          ([key, values]) => {
                                            if (!values || typeof values !== "object") {
                                              return null;
                                            }

                                            const label = key
                                              .replaceAll("_", " ")
                                              .replace(/^./, character => character.toUpperCase());

                                            return (
                                              <div className="mn-ai-target-item" key={key}>
                                                <span className="mn-ai-target-label">{label}</span>
                                                <div className="mn-ai-target-values">
                                                  <div>
                                                    <small>{t("Baseline", "Intangiriro")}</small>
                                                    <strong>{renderAskValue(values.baseline) ?? "—"}</strong>
                                                  </div>
                                                  <div>
                                                    <small>{t("Mid-term", "Hagati")}</small>
                                                    <strong>{renderAskValue(values.mid_term_target) ?? "—"}</strong>
                                                  </div>
                                                  <div>
                                                    <small>{t("End-term", "Iherezo")}</small>
                                                    <strong>{renderAskValue(values.end_term_target) ?? "—"}</strong>
                                                  </div>
                                                </div>
                                                <small className="mn-ai-target-unit">
                                                  {values.unit || t("Unit not specified", "Igipimo nticyagaragajwe")}
                                                </small>
                                              </div>
                                            );
                                          }
                                        )}
                                      </div>

                                      {item.note && (
                                        <p className="mn-ai-evidence-note">{item.note}</p>
                                      )}
                                    </>
                                  ) : hasBasicFacts ? (
                                    <>
                                      <div className="mn-ai-evidence-card-heading">
                                        <span className="mn-ai-evidence-symbol">✓</span>
                                        <div>
                                          <span className="mn-ai-detail-label">
                                            {t("VERIFIED SOURCE RECORD", "INYANDIKO YO MU NKOMOKO")}
                                          </span>
                                          <h4>
                                            {item.district
                                              ? `${item.district}${item.crop ? ` · ${rw ? displayCropName(item.crop) : item.crop}` : ""}`
                                              : item.crop
                                                ? (rw ? displayCropName(item.crop) : item.crop)
                                                : t("Supporting record", "Inyandiko ishyigikira igisubizo")}
                                          </h4>
                                        </div>
                                      </div>

                                      <dl className="mn-ai-evidence-facts">
                                        {fields.map(([key, label]) => {
                                          const value = item?.[key];
                                          if (value == null || value === "") return null;

                                          let displayValue = value;
                                          if (key === "crop" && rw) {
                                            displayValue = displayCropName(value);
                                          }
                                          if (key === "production_mt") {
                                            displayValue = `${new Intl.NumberFormat(
                                              rw ? "rw-RW" : "en-US",
                                              { maximumFractionDigits: 2 }
                                            ).format(Number(value))} ${t("metric tonnes", "toni")}`;
                                          }
                                          if (key === "value_status") {
                                            displayValue = String(value).replaceAll("_", " ").toLowerCase();
                                          }

                                          return (
                                            <div key={key}>
                                              <dt>{label}</dt>
                                              <dd>{displayValue}</dd>
                                            </div>
                                          );
                                        })}
                                      </dl>
                                    </>
                                  ) : (
                                    <p className="mn-ai-evidence-note">
                                      {t(
                                        "Supporting evidence is available, but its fields cannot yet be displayed as a standard record.",
                                        "Ibimenyetso birahari, ariko imiterere yabyo ntirashobora kugaragazwa nk'inyandiko isanzwe."
                                      )}
                                    </p>
                                  )}
                                </article>
                              );
                            })}
                          </div>
                        </details>
                      )}

                      {askResult.limitation && (
                        <div className="mn-ai-limitation">
                          <strong>{t("Limitations", "Imbogamizi")}</strong>
                          <p>{renderAskValue(askResult.limitation)}</p>
                        </div>
                      )}

                      <div className="mn-ai-trust-note">
                        <span aria-hidden="true">ⓘ</span>
                        {t("Historical records are not live market prices, weather forecasts, or official disaster warnings.", "Amakuru yo mu bihe byashize si ibiciro byo ku isoko by'ako kanya, iteganyagihe cyangwa imiburo yemewe y'ibiza.")}
                      </div>
                    </article>
                  )}
                </div>

                <form className="mn-ai-composer" onSubmit={(event) => { event.preventDefault(); submitAsk(); }}>
                  <label className="mn-ai-sr-only" htmlFor="mn-ai-question">
                    {t("Your question", "Ikibazo cyawe")}
                  </label>
                  <textarea
                    id="mn-ai-question"
                    value={askDraft}
                    onChange={(event) => setAskDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        submitAsk();
                      }
                    }}
                    placeholder={t("Ask about maize, beans, a district, a season, or NST2…", "Baza ku bigori, ibishyimbo, akarere, igihembwe cyangwa NST2…")}
                    rows={2}
                    maxLength={1000}
                    disabled={askLoading}
                  />
                  <button type="submit" disabled={askLoading || !askDraft.trim()} aria-label={t("Send question", "Ohereza ikibazo")}>
                    {askLoading ? <span className="mn-ai-spinner mn-ai-spinner-light" /> : <span aria-hidden="true">↑</span>}
                    <span>{t("Ask", "Baza")}</span>
                  </button>
                  <div className="mn-ai-composer-hint">
                    {t("Enter to send · Shift + Enter for a new line", "Enter wohereza · Shift + Enter ugatangira umurongo mushya")}
                    <span>{askDraft.length}/1000</span>
                  </div>
                </form>
              </main>

              <aside className="mn-ai-side-panel">
                <div className="mn-ai-side-heading">
                  <span className="mn-ai-side-symbol" aria-hidden="true">✧</span>
                  <div>
                    <h3>{t("Explore a question", "Hitamo ikibazo")}</h3>
                    <p>{t("Select a prompt to ask it directly.", "Hitamo ikibazo kugira ngo ugihite ubaza.")}</p>
                  </div>
                </div>

                <div className="mn-ai-suggestions">
                  {askSuggestions.map((item) => (
                    <button
                      type="button"
                      key={item.en}
                      onClick={() => submitAsk(rw ? item.rwText : item.en)}
                      disabled={askLoading}
                    >
                      <span className="home-suggestion-icon" aria-hidden="true">{item.icon}</span>
                      <span className="mn-ai-suggestion-copy">
                        <b>{rw ? item.rwText : item.en}</b>
                        <small>{t("Ask this question", "Baza iki kibazo")}</small>
                      </span>
                      <span className="home-suggestion-arrow" aria-hidden="true">↗</span>
                    </button>
                  ))}
                </div>

                <div className="mn-ai-coverage">
                  <span className="mn-ai-detail-label">{t("CURRENT KNOWLEDGE", "AMAKURU AHARI")}</span>
                  <div><i aria-hidden="true">✓</i><span>{t("Crop production records", "Imibare y'umusaruro w'ibihingwa")}</span></div>
                  <div><i aria-hidden="true">✓</i><span>{t("District and season comparisons", "Kugereranya uturere n'ibihembwe")}</span></div>
                  <div><i aria-hidden="true">✓</i><span>{t("Selected NST2 reference indicators", "Ibipimo bimwe bya NST2")}</span></div>
                  <div><i aria-hidden="true">✓</i><span>{t("Data quality and limitations", "Ubwiza bw'amakuru n'imbogamizi")}</span></div>
                  <div className="mn-ai-coverage-limited"><i aria-hidden="true">!</i><span>{t("No verified live weather or official warnings", "Nta iteganyagihe cyangwa miburo yemewe y'ako kanya")}</span></div>
                </div>

                {askHistory.length > 0 && (
                  <div className="mn-ai-history">
                    <div className="mn-ai-history-heading">
                      <span className="mn-ai-detail-label">{t("THIS SESSION", "IKI GIKORWA")}</span>
                      <button type="button" onClick={() => { setAskHistory([]); setAskResult(null); setAskError(""); }} disabled={askLoading}>
                        {t("Clear", "Siba")}
                      </button>
                    </div>
                    {askHistory.slice(-3).reverse().map((item) => (
                      <button className="mn-ai-history-item" type="button" key={item.id} onClick={() => { setAskDraft(item.question); setAskResult(item.result); setAskError(""); }}>
                        <span>{item.question}</span><span aria-hidden="true">↗</span>
                      </button>
                    ))}
                  </div>
                )}
              </aside>
            </div>
          </section>

          <section className="home-evidence">
            <div className="home-evidence-heading">
              <span className="section-kicker">{t("BUILT AROUND EVIDENCE", "ISHINGIYE KU BIMENYETSO")}</span>
              <h2>
                {t("Intelligence you can", "Amakuru ushobora")}
                <br />
                <em>{t("inspect and understand.", "gusuzuma no gusobanukirwa.")}</em>
              </h2>
              <p>
                {t(
                  "Not just numbers on a screen. Explore the source, understand the period, and see what the available evidence can—and cannot—tell you.",
                  "Si imibare gusa iri kuri ecran. Reba inkomoko yayo, menya igihe yakusanyirijwe, kandi usobanukirwe n'ibyo amakuru ahari ashobora cyangwa adashobora kukubwira."
                )}
              </p>
            </div>

            <div className="home-evidence-grid">
              <button className="home-evidence-card" onClick={() => navigate("area")}>
                <span className="home-evidence-number">01</span>
                <span className="home-evidence-icon">⌖</span>
                <h3>{t("Understand your area", "Sobanukirwa n'akarere kawe")}</h3>
                <p>{t("Explore reported crop-production figures by district and agricultural season.", "Reba imibare y'umusaruro w'ibihingwa yatangajwe hakurikijwe akarere n'igihembwe.")}</p>
                <span className="home-evidence-link">{t("Explore district data", "Reba amakuru y'akarere")} →</span>
              </button>

              <button className="home-evidence-card" onClick={() => navigate("seasonal")}>
                <span className="home-evidence-number">02</span>
                <span className="home-evidence-icon">◷</span>
                <h3>{t("See seasonal patterns", "Reba imiterere y'ibihembwe")}</h3>
                <p>{t("Compare the reported figures for Seasons A, B, and C without treating them as a live forecast.", "Gereranya imibare yatangajwe mu bihembwe A, B na C utayifata nk'iteganyagihe ry'ubu.")}</p>
                <span className="home-evidence-link">{t("Compare seasons", "Gereranya ibihembwe")} →</span>
              </button>

              <button className="home-evidence-card" onClick={() => navigate("origins")}>
                <span className="home-evidence-number">03</span>
                <span className="home-evidence-icon">⌁</span>
                <h3>{t("Explore supply origins", "Menya aho umusaruro ukomoka")}</h3>
                <p>{t("Inspect where production was reported, with incomplete district records clearly identified.", "Reba aho umusaruro watangajwe, unamenye uturere dufite imibare ituzuye.")}</p>
                <span className="home-evidence-link">{t("Explore origins", "Reba aho umusaruro ukomoka")} →</span>
              </button>
            </div>
          </section>

          <section className="home-method">
            <div className="home-method-copy">
              <span className="section-kicker">{t("FROM DATA TO EARLY ACTION", "DUHERE KU MAKURU TUGERE KU KWITEGURA")}</span>
              <h2>{t("Understand the evidence.", "Sobanukirwa n'ibimenyetso.")}<br /><em>{t("Know its limits.", "Menya aho bigarukira.")}</em></h2>
              <p>
                {t(
                  "Our approach connects data exploration with clear explanations. As the platform grows, new risk information must be sourced and validated before it can support warnings or recommendations.",
                  "Uburyo dukoresha buhuza gushakisha amakuru no kuyasobanura neza. Uko urubuga ruzagenda rwaguka, amakuru mashya ku byago agomba kubanza kubona inkomoko no kwemezwa mbere yo gukoreshwa mu miburo cyangwa inama."
                )}
              </p>
              <button className="principle-link" onClick={() => navigate("about")}>
                {t("How MENYA NEZA works", "Uko MENYA NEZA ikora")} <span>→</span>
              </button>
            </div>

            <div className="home-method-steps">
              {[
                ["01", "DATA", "Start with traceable information.", "Tangira ku makuru afite inkomoko izwi."],
                ["02", "DETECT", "Identify patterns the data supports.", "Menya imiterere igaragazwa n'amakuru."],
                ["03", "EXPLAIN", "Show the evidence and uncertainty.", "Garagaza ibimenyetso n'ibitaramenyekana."],
                ["04", "PREPARE", "Help people explore informed next steps.", "Fasha abantu gusuzuma intambwe zikurikira."]
              ].map(([number, title, en, rwText]) => (
                <div className="home-method-step" key={number}>
                  <span className="home-step-number">{number}</span>
                  <div>
                    <b>{title}</b>
                    <p>{t(en, rwText)}</p>
                  </div>
                  <span className="home-step-arrow">↗</span>
                </div>
              ))}
            </div>
          </section>

          <section className="home-principle">
            <div className="principle-mark">✓</div>
            <div>
              <span className="section-kicker">{t("TRUST THROUGH TRANSPARENCY", "ICYIZERE GISHINGIYE KU BUSOBANURO")}</span>
              <h2>
                {t("Evidence before conclusions.", "Ibimenyetso mbere y'imyanzuro.")}
                <br />
                <em>{t("People before promises.", "Abantu mbere y'amasezerano.")}</em>
              </h2>
            </div>
            <p>
              {t(
                "The current platform uses historical NISR SAS 2025 crop-production data and separate market-price summaries with limitations. It does not yet provide validated disaster predictions, live weather, or official warnings.",
                "Ubu urubuga rukoresha amakuru y'umusaruro yo muri NISR SAS 2025 n'incamake z'ibiciro ku masoko zitandukanye zifite imbogamizi. Ntiruratanga ibyahanuwe byemejwe ku biza, amakuru y'ikirere y'ako kanya, cyangwa imbuzi zemewe."
              )}
            </p>
            <button className="principle-link" onClick={() => navigate("quality")}>
              {t("Review sources and limitations", "Reba amasoko n'imbogamizi")} <span>→</span>
            </button>
          </section>
        </main>
      )}
      {page === "area" && (
        <main className="inner-page">
          <button className="back-link" onClick={() => navigate("home")}>← Garuka ku ntangiriro</button>
          <div className="inner-heading">
            <span className="section-kicker">{t("YOUR AREA, YOUR INFORMATION", "AKARERE KAWE, AMAKURU YAWE")}</span>
            <h1>{t("Explore", "Menya")} <em>{t("your area.", "akarere kawe.")}</em></h1>
            <p>{t("Explore historical crop-production observations for a district in Rwanda.", "Reba imibare y'umusaruro w'ibihingwa mu karere ko mu Rwanda, yakusanyijwe mu bihe byashize.")}</p>
          </div>

          <div className="explorer-card">
            <div className="explorer-controls">
              <label>{t("District", "Akarere")}
                <select value={district} onChange={e => setDistrict(e.target.value)}>
                  {districts.map(d => <option key={d}>{d}</option>)}
                </select>
              </label>
              <label>{t("Season", "Igihembwe cy’ubuhinzi")}
                <select value={season} onChange={e => setSeason(e.target.value)}>
                  {Object.entries(seasons).map(([key, period]) =>
                    <option key={key} value={key}>{t("Season", "Igihembwe")} {key} · {period}</option>
                  )}
                </select>
              </label>
            </div>
            <div className="data-context">
              <span className="context-icon">i</span>
              {t("NISR Seasonal Agricultural Survey 2025", "Ubushakashatsi bwa NISR ku buhinzi, 2025")} · {seasons[season]} · {t("Metric tonnes (MT)", "Toni (MT)")}
            </div>
          </div>

          {loading ? <div className="state-panel">{t("Loading agricultural data…", "Amakuru y'ubuhinzi arimo gutegurwa…")}</div> :
            error ? <div className="state-panel error-panel">{errorMessage(error)}</div> : <>
              <div className="area-summary">
                <div><span>{t("SELECTED DISTRICT", "AKARERE KATORANYIJWE")}</span><h2>{district}</h2><small>{t("Season", "Igihembwe")} {season} · {seasons[season]}</small></div>
                <div className="history-badge"><span /> {t("HISTORICAL DATA", "AMAKURU YO MU BIHE BYASHIZE")}</div>
              </div>
              <div className="stat-grid">
                <article className="stat-card stat-primary">
                  <span className="stat-label">{t("Largest reported category", "Icyiciro gifite umubare munini watangajwe")}</span>
                  <strong>{crops[0] ? displayCropName(crops[0].name) : t("No reported crop", "Nta gihingwa cyatangajwe")}</strong>
                  <p>{crops[0] ? `${fmt(crops[0].value)} MT` : "—"}</p>
                  <p>{t("Largest numeric value among the reported categories for this district and season; some categories may overlap.", "Umubare munini mu byiciro byatangajwe muri aka karere no muri iki gihembwe; hari ibyiciro bishobora kuba bifitanye isano.")}</p>
                </article>
                <article className="stat-card">
                  <span className="stat-label">{t("Reported crop categories", "Ibyiciro by'ibihingwa bifite imibare")}</span>
                  <strong>{crops.length}<small> / {t("categories", "byiciro")}</small></strong>
                  <p>{t("Categories with numeric production values in the selected district, season, and year.", "Ibyiciro bifite imibare y’umusaruro mu karere, igihembwe n’umwaka wahisemo.")}</p>
                </article>
                <article className="stat-card">
                  <span className="stat-label">{t("Reported records", "Imibare yatanzwe")}</span>
                  <strong>{area.length ? Math.round(reported / area.length * 100) : 0}<small>%</small></strong>
                  <p>{reported} {t("reported", "byatangajwe")} · {missing} {t("not reported", "bitatangajwe")} {t("out of", "muri")} {area.length} {t("records", "y’imibare")}.</p>
                  <div className="coverage-track"><span style={{width: `${area.length ? reported / area.length * 100 : 0}%`}} /></div>
                </article>
              </div>

              <ExplainThis
                en="These figures describe the selected district and season in the 2025 survey. The percentage is the share of records with reported numeric values out of all records loaded for this selection. Missing values are not zero. The chart compares reported categories; some categories may overlap, so do not add them together. These historical figures do not establish current food stocks, market availability, or household food sufficiency."
                rwText="Iyi mibare igaragaza akarere n’igihembwe wahisemo mu bushakashatsi bwa 2025. Ijanisha rigaragaza igipimo cy’imibare yatanzwe ifite agaciro k’imibare ugereranyije n’imibare yose iri mu byo wahisemo. Imibare ibura ntifatwa nka zeru. Ibyiciro bimwe bishobora kuba bifitanye isano, bityo ntibikwiye guteranywa. Iyi mibare yo mu bihe byashize ntiyemeza ububiko bw’ibiribwa buriho ubu, ibiboneka ku isoko, cyangwa ko ingo zifite ibiribwa bihagije."
              />

              <div className="data-layout">
                <article className="chart-card">
                  <div className="card-heading"><div><span className="section-kicker">{t("CROP BREAKDOWN", "UMUSARURO UKURIKIJE IGIHINGWA")}</span><h3>{t("Reported production by crop", "Umusaruro watangajwe kuri buri gihingwa")}</h3></div><span className="unit-label">MT</span></div>
                  {crops.length ? <div className="bar-chart">{crops.slice(0, 10).map((crop, i) =>
                    <div className="bar-row" key={crop.name}>
                      <div className="bar-title"><span>{displayCropName(crop.name)}</span><b>{fmt(crop.value)}</b></div>
                      <div className="bar-track"><span className={i === 0 ? "bar-fill bar-fill-main" : "bar-fill"} style={{width: `${Math.max(1.5, crop.value / max * 100)}%`}} /></div>
                    </div>
                  )}</div> : <p className="empty-state">{t("No numeric values are available for this selection.", "Nta mibare iboneka ku byo wahisemo.")}</p>}
                  <p className="chart-footnote">{t("Missing values are not treated as zero. Some reported categories are aggregates alongside their component categories (for example, Banana and its three types). Do not add these figures together; the chart compares reported labels, not mutually exclusive crop groups.", "Amakuru abura ntafatwa nka zeru. Ibyiciro bimwe bishobora kuba ari igiteranyo cy’ubwoko bugaragazwa ukwabwo, urugero Banana n’ubwoko bwayo butatu. Ntuteranye iyi mibare; igishushanyo kigereranya ibyiciro byatangajwe, kandi si ngombwa ko buri cyiciro kiba cyigenga ku kindi.")}</p>
                </article>
                <aside className="insight-column">
                  <article className="insight-card"><span className="section-kicker">{t("LARGEST REPORTED CATEGORY", "ICYICIRO GIFITE UMUBARE MUNINI MU YATANZWE")}</span><h3>{crops[0] ? displayCropName(crops[0].name) : t("No reported crop", "Nta gihingwa cyatangajwe")}</h3><strong>{crops[0] ? `${fmt(crops[0].value)} MT` : "—"}</strong><p>{t("The largest numeric value among the categories reported for this selection. It is not a risk score.", "Uyu ni wo mubare munini mu byiciro byatangajwe ku byo wahisemo. Ntabwo ari amanota agaragaza ibyago.")}</p></article>
                  <article className="plain-note"><span className="note-icon">i</span><div><b>{t("Understand these figures", "Sobanukirwa n'iyi mibare")}</b><p>{crops[0] ? t(`In ${district}, during Season ${season}, ${crops[0].name} has the largest reported production value in this selection (${fmt(crops[0].value)} MT). This alone does not show whether households have enough food.`, `Mu karere ka ${district}, mu gihembwe cya ${season}, icyiciro cya ${displayCropName(crops[0].name)} ni cyo gifite umusaruro mwinshi mu mibare yatangajwe (${fmt(crops[0].value)} toni). Ibi byonyine ntibihagije kwemeza ko abaturage bafite ibiribwa bihagije.`) : t("No reported crop value is available for this selection.", "Nta mubare w'umusaruro watangajwe uboneka ku byo wahisemo.")}</p></div></article>
                  <article className="data-warning"><span className="warning-icon">!</span><div><b>{t("Data limitation", "Imbogamizi z'amakuru")}</b><p>{t("Some values were not reported in the source. The meaning of source dashes requires confirmation.", "Hari imibare itagaragajwe mu nyandiko y'inkomoko. Ibisobanuro by'utudomo cyangwa imirongo ikoreshwa aho imibare ibura bigomba kubanza kwemezwa.")}</p></div></article>
                </aside>
              </div>
            </>}
        </main>
      )}

      {page === "insights" && (
        <main className="inner-page">
          <button className="back-link" onClick={() => navigate("home")}>← Garuka ku ntangiriro</button>
          <div className="inner-heading">
            <span className="section-kicker">{t("INSTITUTIONAL WORKSPACE", "AHAGENEWE ABAKURIKIRANA N'ABASESENGURA AMAKURU")}</span>
            <h1>Data <em>{t("Insights.", "n'isesengura.")}</em></h1>
            <p>{t("Review the coverage and consistency of the current SAS 2025 crop-production extract.", "Suzuma amakuru aboneka n'uko ahura mu mibare y'umusaruro w'ibihingwa yakusanyijwe muri SAS 2025.")}</p>
          </div>
          {loading ? <div className="state-panel">{t("Loading datasets…", "Amakuru arimo gutegurwa…")}</div> : error ? <div className="state-panel error-panel">{errorMessage(error)}</div> : <>
            <div className="stat-grid">
              <article className="stat-card stat-primary"><span className="stat-label">{t("District-level records", "Imibare yakusanyijwe ku rwego rw'uturere")}</span><strong>{fmt(records.length)}</strong><p>{t("Records extracted across three agricultural seasons.", "Imibare yakusanyijwe mu bihembwe bitatu by'ubuhinzi.")}</p></article>
              <article className="stat-card"><span className="stat-label">{t("Checks with reported district values", "Igenzura ry'imibare y'uturere yatanzwe")}</span><strong>{completeChecks}<small> / {checks.length}</small></strong><p>{t("Not all checks necessarily reconcile with national totals.", "Si buri genzura ryose rigomba guhura n'igiteranyo cyatangajwe ku rwego rw'igihugu.")}</p></article>
              <article className="stat-card"><span className="stat-label">{t("Incomplete checks", "Igenzura rituzuye")}</span><strong>{checks.length - completeChecks}</strong><p>{t("At least one district value was not reported.", "Nibura umubare umwe w'akarere ntiwatanzwe.")}</p></article>
            </div>
            <ExplainThis
              en="A district-level record is one extracted crop observation, not one person or one farm. Checks counted as not incomplete can still need review; they are not all confirmed matches. Seasonal percentages describe whether values were reported in this dataset, not crop success, food security, or disaster risk."
              rwText="Umubare wo ku rwego rw'akarere ni amakuru y'igihingwa yakusanyijwe, si umuntu umwe cyangwa umurima umwe. Igenzura ritashyizwe mu bituzuye na ryo rishobora kuba rigikeneye gusuzumwa; ntibivuze ko ryose ryemejwe ko rihuye. Ijanisha rya buri gihembwe rigaragaza amakuru yatanzwe muri iyi dosiye, si intsinzi y'ubuhinzi, umutekano w'ibiribwa cyangwa ibyago by'ibiza."
            />
            <article className="chart-card seasonal-card">
              <div className="card-heading"><div><span className="section-kicker">{t("SEASONAL COVERAGE", "AMAKURU ABONEKA KURI BURI GIHEMBWE")}</span><h3>{t("Source-reported records by season", "Imibare yatanzwe n’inkomoko kuri buri gihembwe")}</h3></div></div>
              <div className="season-grid">{Object.entries(seasons).map(([key, period]) => {
                const rows = records.filter(r => r.season === key);
                const count = rows.filter(r => r.source_value_status === "reported").length;
                const pct = rows.length ? Math.round(count / rows.length * 100) : 0;
                return <div className="season-box" key={key}><span>{t("Season", "Igihembwe")} {key}</span><strong>{pct}%</strong><div className="bar-track"><span className="bar-fill bar-fill-main" style={{width: `${pct}%`}} /></div><small>{count} {t("of", "muri")} {rows.length} {t("observations reported", "byatangajwe")}</small><small>{period}</small></div>;
              })}</div>
              <p className="chart-footnote">{t(
                "Percentages show data availability in the source, not crop performance or disaster risk.",
                "Ijanisha ryerekana amakuru aboneka mu nyandiko y’inkomoko, si uko umusaruro uhagaze cyangwa ibyago by’ibiza."
              )}</p>
            </article>
            <ExplainThis
              en="These are project checks comparing available district sums with source national totals where comparison is possible. MATCH means the checked figures agree under this project's validation rules. REVIEW statuses need investigation; incomplete district data are not treated as a confirmed mismatch."
              rwText="Iri ni igenzura ry'umushinga rigereranya igiteranyo cy'uturere n'imibare rusange yo mu nyandiko y'inkomoko igihe bishoboka. MATCH bivuga ko imibare ihuye hakurikijwe amategeko y'iri genzura. Ibyiciro bya REVIEW biracyakeneye gusuzumwa; amakuru y'uturere atuzuye ntifatwa nk'uko byemejwe ko imibare idahuye."
            />
            <article className="chart-card validation-card">
              <div className="card-heading"><div><span className="section-kicker">{t("QUALITY REVIEW", "ISUZUMA RY'UBWIZA BW'AMAKURU")}</span><h3>{t("National-total validation checks", "Igenzura ry'igiteranyo cy'igihugu")}</h3></div></div>
              <p className="muted-copy">{t("These are project diagnostic checks, not official NISR classifications. Incomplete district sums are not compared with national totals.", "Aya ni igenzura ryakozwe muri uyu mushinga, si ibyiciro byemejwe na NISR. Igiteranyo cy'uturere gifite amakuru abura ntikigereranywa n'igiteranyo cy'igihugu.")}</p>
              <div className="validation-list">{checks.slice(0, 15).map((r, i) =>
                <div className="validation-row" key={`${r.season}-${r.crop}-${i}`}>
                  <div><b>{displayCropName(r.crop)}</b><small>{t("Season", "Igihembwe")} {r.season} · {r.year}</small></div>
                  <span className={`validation-status ${r.validation_status === "MATCH" ? "status-match" : r.validation_status === "INCOMPLETE_DISTRICT_DATA" ? "status-incomplete" : "status-review"}`}>{r.validation_status === "MATCH"
                    ? t("Match", "Birahuye")
                    : r.validation_status === "INCOMPLETE_DISTRICT_DATA"
                      ? t("Incomplete district data", "Amakuru y'uturere atuzuye")
                      : t("Needs review", "Bikeneye kugenzurwa")}</span>
                  <span className="difference">{r.difference_mt == null || r.difference_mt === "" ? t("Not compared", "Ntabwo byagereranyijwe") : `${fmt(Number(r.difference_mt))} MT`}</span>
                </div>
              )}</div>
              <p className="chart-footnote">{t("First 15 checks shown. The full validation dataset remains in the project CSV.", "Hagaragajwe igenzura 15 rya mbere. Amakuru yose y'igenzura abitswe muri dosiye ya CSV y'umushinga.")}</p>
            </article>
          </>}
        </main>
      )}

      {page === "origins" && (
        <main className="inner-page origins-page">
          <button className="back-link" onClick={() => navigate("home")}>
            ← {t("Back to home", "Garuka ku ntangiriro")}
          </button>

          <div className="inner-heading">
            <span className="section-kicker">
              {t("RWANDA AGRICULTURAL SUPPLY", "UMUSARURO W'UBUHINZI MU RWANDA")}
            </span>
            <h1>{t("Supply", "Aho umusaruro")} <em>{t("origins.", "ukomoka.")}</em></h1>
            <p>{t(
              "Compare crop-production figures reported for Rwanda's districts in the 2025 seasonal survey.",
              "Gereranya imibare y'umusaruro w'ibihingwa yatangajwe mu turere tw'u Rwanda muri SAS 2025."
            )}</p>
          </div>

          <section className="chart-card origins-explorer">
            <div className="origins-controls">
              <label>
                <span>{t("Crop", "Igihingwa")}</span>
                <select value={originCrop}
                  onChange={e => setOriginCrop(e.target.value)}>
                  {originCrops.map(crop => (
                    <option key={crop} value={crop}>{displayCropName(crop)}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>{t("Season", "Igihembwe")}</span>
                <select value={originSeason}
                  onChange={e => setOriginSeason(e.target.value)}>
                  {Object.entries(seasons).map(([key, period]) => (
                    <option key={key} value={key}>
                      {t("Season", "Igihembwe")} {key} — {period}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="origins-period">
              {t("Survey period", "Igihe cy'ubushakashatsi")}:{" "}
              {seasons[originSeason]} · 2025
            </p>
          </section>

          {originsLoading && (
            <div className="state-panel">
              {t("Loading district production figures…", "Amakuru y'umusaruro w'uturere arimo gutegurwa…")}
            </div>
          )}

          {!originsLoading && originsError && (
            <div className="state-panel error-panel">
              {t(
                "Supply-origin data could not be loaded. Check that the backend API is running, then try again.",
                "Amakuru y'aho umusaruro ukomoka ntiyabashije kuboneka. Reba niba backend API iri gukora, wongere ugerageze."
              )}
              <button className="primary-button origins-retry"
                onClick={() => {
                  setOriginsError("");
                  setPage("home");
                  window.setTimeout(() => setPage("origins"), 0);
                }}>
                {t("Try again", "Ongera ugerageze")}
              </button>
            </div>
          )}

          {!originsLoading && !originsError && origins && (
            <>
              <div className="stat-grid origins-stat-grid">
                <article className="stat-card stat-primary">
                  <span className="stat-label">{t("Districts with reported values", "Uturere twatangaje imibare")}</span>
                  <strong>{fmt(origins.summary.reported_records)}<small> / {fmt(origins.summary.expected_districts_in_dataset)}</small></strong>
                  <p>{t("District production values available in this selection.", "Imibare y'umusaruro w'uturere iboneka ku byo wahisemo.")}</p>
                </article>
                <article className="stat-card">
                  <span className="stat-label">{t("Reported subtotal", "Igiteranyo cy'imibare yatangajwe")}</span>
                  <strong>{fmt(origins.summary.reported_district_subtotal_mt)}<small> MT</small></strong>
                  <p>{t("Sum of reported district values, not necessarily a national total.", "Igiteranyo cy'imibare yatangajwe n'uturere; si ngombwa ko ari igiteranyo cy'igihugu.")}</p>
                </article>
                <article className="stat-card">
                  <span className="stat-label">{t("Values not reported", "Imibare itaratangajwe")}</span>
                  <strong>{fmt(origins.summary.missing_production_records)}</strong>
                  <p>{t("Missing values are not treated as zero.", "Imibare ibura ntifatwa nka zeru.")}</p>
                </article>
              </div>

                <ExplainThis
                  en="Choose a crop and season to compare the 2025 survey figures. Districts with reported numeric values are ranked from highest to lowest. A missing value is unknown, not zero; the reported subtotal may exclude missing districts and is not automatically the official national total. These historical figures do not show current market availability."
                  rwText="Hitamo igihingwa n'igihembwe kugira ngo ugereranye imibare y'ubushakashatsi bwa 2025. Uturere twatangaje imibare tugaragazwa kuva ku munini kugera ku muto. Umubare ubura ntuzwi, si zeru; igiteranyo gishobora kutarimo uturere tutatanze imibare kandi si ngombwa ko gihwanye n'igiteranyo cyemewe cy'igihugu. Iyi mibare yo mu bihe byashize ntigaragaza ibiri ku isoko ubu."
                />
              <section className="chart-card origins-ranking">
                <div className="card-heading">
                  <div>
                    <span className="section-kicker">{t("DISTRICT COMPARISON", "IGERERANYA RY'UTURERE")}</span>
                    <h3>{displayCropName(origins.filters.crop)} — {t("reported production", "umusaruro watangajwe")}</h3>
                  </div>
                  <span className="origins-unit">{t("Metric tonnes (MT)", "Toni (MT)")}</span>
                </div>

                <p className="muted-copy">
                  {t(
                    "Districts with numeric values are ranked from highest to lowest. Unreported values appear last without a rank.",
                    "Uturere dufite imibare yemewe mu nyandiko bigaragara kuva ku musaruro munini kugera ku muto. Imibare itaratangajwe igaragara hasi idafite umwanya."
                  )}
                </p>

                <div className="origins-table-wrap">
                  <table className="origins-table">
                    <thead>
                      <tr>
                        <th>{t("Rank", "Umwanya")}</th>
                        <th>{t("District", "Akarere")}</th>
                        <th>{t("Production (MT)", "Umusaruro (MT)")}</th>
                        <th>{t("Reporting", "Imiterere y'amakuru")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {origins.districts.map((row, index) => (
                        <tr key={`${row.district}-${index}`}>
                          <td>{row.rank ?? "—"}</td>
                          <td>{row.district}</td>
                          <td className="origins-value">
                            {row.production_mt == null
                              ? t("Not reported", "Ntabwo byatangajwe")
                              : fmt(row.production_mt)}
                          </td>
                          <td>
                            <span className={
                              row.production_mt == null
                                ? "origins-status missing"
                                : "origins-status reported"
                            }>
                              {row.production_mt == null
                                ? t("Missing", "Birabura")
                                : t("Reported", "Byatangajwe")}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <p className="chart-footnote">
                  {t(
                    `Source: ${origins.source}. Table ${origins.districts.find(r => r.source_table != null)?.source_table ?? "not specified"}; page ${origins.districts.find(r => r.source_page != null)?.source_page ?? "not specified"}.`,
                    `Inkomoko: ${origins.source}. Imbonerahamwe ${origins.districts.find(r => r.source_table != null)?.source_table ?? "ntiyagaragajwe"}; urupapuro ${origins.districts.find(r => r.source_page != null)?.source_page ?? "ntirwagaragajwe"}.`
                  )}
                </p>
              </section>

              <div className="about-notice origins-notice">
                <b>{t("Important interpretation", "Icyitonderwa")}</b>
                <p>{t(
                  "These are historical production figures for the selected survey season. They do not show current stocks, market availability, prices, or confirmed suppliers. A district subtotal is not automatically the published national total.",
                  "Iyi ni imibare y'umusaruro wo mu gihembwe cy'ubushakashatsi cyatoranyijwe. Ntigaragaza ububiko bw'ibiribwa buriho ubu, ibiri ku isoko, ibiciro cyangwa abatanga ibicuruzwa bemejwe. Igiteranyo cy'uturere si ngombwa ko gihwanye n'igiteranyo cyatangajwe ku rwego rw'igihugu."
                )}</p>
              </div>
            </>
          )}
        </main>
      )}


      {page === "seasonal" && (
        <main className="inner-page seasonal-comparison-page">
          <button className="back-link" onClick={() => navigate("home")}>
            {t("← Back to home", "← Garuka ku ntangiriro")}
          </button>

          <div className="inner-heading">
            <span className="section-kicker">
              {t("HISTORICAL AGRICULTURAL DATA", "IMIBARE Y'UBUHINZI YO MU BIHE BYASHIZE")}
            </span>
            <h1>
              {t("Compare agricultural ", "Gereranya ")}
              <em>{t("seasons.", "ibihembwe by'ubuhinzi.")}</em>
            </h1>
            <p>
              {t(
                "Explore reported crop-production figures across Seasons A, B, and C in the 2025 NISR Seasonal Agricultural Survey.",
                "Reba imibare y'umusaruro w'ibihingwa yatangajwe mu bihembwe A, B na C by'ubushakashatsi bwa NISR bwo mu 2025."
              )}
            </p>
          </div>

          <section className="about-card seasonal-selector-card">
            <label className="seasonal-select-label" htmlFor="seasonal-crop-select">
              {t("Choose a crop", "Hitamo igihingwa")}
            </label>
            <select
              id="seasonal-crop-select"
              value={seasonalCrop}
              onChange={(event) => setSeasonalCrop(event.target.value)}
            >
              {(seasonalData?.available_crops?.length
                ? seasonalData.available_crops
                : ["Beans", "Bush bean", "Climbing bean", "Irish potatoes", "Sweet potatoes", "Vegetables"]
              ).map((crop) => (
                <option key={crop} value={crop}>{displayCropName(crop)}</option>
              ))}
            </select>
            <p className="origins-period">
              {t("Survey year: 2025 · Unit: metric tonnes (MT)",
                 "Umwaka w'ubushakashatsi: 2025 · Igipimo: toni (MT)")}
            </p>
          </section>

          {seasonalLoading && (
            <div className="state-panel">
              {t("Loading verified seasonal figures…", "Turimo kuzana imibare y'ibihembwe yagenzuwe…")}
            </div>
          )}

          {!seasonalLoading && seasonalError && (
            <div className="state-panel error-panel">
              <p>
                {t(
                  "The seasonal comparison could not be loaded. Check that the API is running and try again.",
                  "Imibare yo kugereranya ibihembwe ntiyabashije kuboneka. Reba niba API iri gukora wongere ugerageze."
                )}
              </p>
              <button className="primary-button" onClick={() => {
                setSeasonalError("");
                setPage("home");
                window.setTimeout(() => setPage("seasonal"), 0);
              }}>
                {t("Try again", "Ongera ugerageze")}
              </button>
            </div>
          )}

          {!seasonalLoading && !seasonalError && seasonalData && (
            <>
              <section className="seasonal-results-section">
                <div className="section-heading-row">
                  <div>
                    <span className="section-kicker">
                      {t("REPORTED DISTRICT SUBTOTALS", "IBITERANYO BY'UTURERE BYATANGAJWE")}
                    </span>
                    <h2>{displayCropName(seasonalData.selected_crop)}</h2>
                  </div>
                  <span className="origins-unit">{seasonalData.unit}</span>
                </div>

                <p className="seasonal-context">
                  {t(
                    "Bar lengths represent reported district subtotals. Read them together with the reporting coverage below; incomplete coverage can make a subtotal look smaller.",
                    "Uburebure bw'utubari bugaragaza ibiteranyo by'uturere byatangajwe. Birebe hamwe n'ubwuzure bw'amakuru; amakuru abura ashobora gutuma igiteranyo gisa n'igitoya."
                  )}
                </p>

                <div className="seasonal-comparison-list">
                  {(() => {
                    const rows = seasonalData.seasons ?? [];
                    const maxSubtotal = Math.max(
                      1,
                      ...rows.map(row => Number(row.reported_district_subtotal_mt) || 0)
                    );

                    return rows.map((row) => {
                      const subtotal = Number(row.reported_district_subtotal_mt) || 0;
                      const coverage = Number(row.district_coverage_percent) || 0;
                      const status = row.validation_status;
                      const statusLabel = status === "MATCH"
                        ? t("Matches published total", "Bihuye n'igiteranyo cyatangajwe")
                        : status === "INCOMPLETE_DISTRICT_DATA"
                          ? t("Incomplete district data", "Amakuru y'uturere ntuzuye")
                          : status === "SMALL_DIFFERENCE_REVIEW"
                            ? t("Small difference — review", "Hari itandukaniro rito — bisuzumwe")
                            : status;

                      return (
                        <article className="seasonal-comparison-card" key={row.season}>
                          <div className="seasonal-row-heading">
                            <div>
                              <span className="seasonal-season-label">
                                {t("SEASON", "IGIHEMBWE")} {row.season}
                              </span>
                              <h3>{row.season_period}</h3>
                            </div>
                            <strong className="seasonal-total">{fmt(subtotal)} <small>MT</small></strong>
                          </div>

                          <div
                            className="seasonal-bar-track"
                            role="img"
                            aria-label={`${t("Reported district subtotal", "Igiteranyo cy'uturere cyatangajwe")}: ${fmt(subtotal)} MT`}
                          >
                            <span style={{ width: `${(subtotal / maxSubtotal) * 100}%` }} />
                          </div>

                          <div className="seasonal-metrics">
                            <div>
                              <span>{t("District coverage", "Amakuru y'uturere ahari")}</span>
                              <strong>{row.reported_districts}/{row.expected_districts} ({fmt(coverage)}%)</strong>
                            </div>
                            <div>
                              <span>{t("Missing districts", "Uturere tuburamo amakuru")}</span>
                              <strong>{row.missing_districts}</strong>
                            </div>
                            <div>
                              <span>{t("Published national total", "Igiteranyo cy'igihugu cyatangajwe")}</span>
                              <strong>
                                {row.published_national_mt == null
                                  ? t("Not available", "Ntibibonetse")
                                  : `${fmt(row.published_national_mt)} MT`}
                              </strong>
                            </div>
                          </div>

                          <div className="seasonal-validation-row">
                            <span className={
                              status === "MATCH"
                                ? "seasonal-status status-match"
                                : "seasonal-status status-review"
                            }>
                              {statusLabel}
                            </span>
                            <span>
                              {t("Table", "Imbonerahamwe")} {row.source_table}
                              {" · "}
                              {t("page", "urupapuro")} {row.source_page}
                            </span>
                          </div>
                        </article>
                      );
                    });
                  })()}
                </div>
              </section>

              <section className="about-notice seasonal-warning">
                <b>{t("How to interpret this comparison", "Uko wasobanura iyi mibare")}</b>
                <p>
                  {t(
                    "Seasons A, B, and C cover different agricultural periods; this is not a year-over-year trend. A reported district subtotal may differ from the published national total. Season C may have fewer reported districts. Missing values are not zero, and historical production does not show current stock, market availability, or a live forecast.",
                    "Ibihembwe A, B na C bihagarariye ibihe bitandukanye by'ubuhinzi; iyi mibare si igereranya ry'imyaka ikurikirana. Igiteranyo cy'uturere cyatangajwe gishobora gutandukana n'icyatangajwe ku rwego rw'igihugu. Mu gihembwe C hashobora kubura uturere twatanze amakuru. Amakuru abura si zeru, kandi umusaruro wo mu bihe byashize ntugaragaza ububiko bw'ubu, ibiri ku isoko cyangwa iteganyagihe."
                  )}
                </p>
              </section>

              <p className="chart-footnote">
                {t("Source: ", "Inkomoko: ")}{seasonalData.source}
                {" · "}
                {t("Year: ", "Umwaka: ")}{seasonalData.year}
              </p>
              <ExplainThis
                en="The district subtotal adds only the values reported for districts. The published national total is shown separately because it is the figure reported by the source publication. Check district coverage and the validation status before drawing conclusions."
                rwText="Igiteranyo cy'uturere gikoresha gusa imibare yatangajwe n'uturere. Igiteranyo cy'igihugu cyatangajwe kigaragazwa ukwacyo kuko ari cyo kiri mu nyandiko y'inkomoko. Reba umubare w'uturere twatanze amakuru n'imiterere y'igenzura mbere yo gufata umwanzuro."
              />
            </>
          )}
        </main>
      )}

      {page === "quality" && (
        <main className="inner-page quality-page">
          <button className="back-link" onClick={() => navigate("home")}>
            ← {t("Back to home", "Garuka ku ntangiriro")}
          </button>

          <div className="inner-heading">
            <span className="section-kicker">
              {t("TRANSPARENCY & TRACEABILITY", "GUSOBANUKIRWA N'INKOMOKO Y'AMAKURU")}
            </span>
            <h1>
              {t("Data quality", "Ubwiza bw'")}{" "}
              <em>{t("& sources.", "amakuru n'inkomoko yayo.")}</em>
            </h1>
            <p>
              {t(
                "Understand what was reported, what needs review, and where the figures came from.",
                "Menya imibare yatanzwe, ikeneye gusuzumwa, n'aho amakuru yakomotse."
              )}
            </p>
          </div>

          {loading ? (
            <div className="state-panel">
              {t("Loading validation records…", "Amakuru y'igenzura arimo gutegurwa…")}
            </div>
          ) : error ? (
            <div className="state-panel error-panel">{errorMessage(error)}</div>
          ) : (
            <>
              <div className="quality-source-note">
                <span className="note-icon">i</span>
                <div>
                  <b>{t("Data source", "Inkomoko y'amakuru")}</b>
                  <p>NISR Seasonal Agricultural Survey 2025</p>
                  <div className="quality-source-links">
                    <a
                      href="https://www.statistics.gov.rw/sites/default/files/documents/2025-12/SAS%202025%20Final%20report.pdf"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {t("Open official NISR report (PDF)", "Fungura raporo ya NISR (PDF)")}
                      <span aria-hidden="true"> ↗</span>
                    </a>
                    <a
                      href="https://microdata.statistics.gov.rw/index.php/catalog/124"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {t("View NISR data catalogue", "Reba ububiko bw'amakuru bwa NISR")}
                      <span aria-hidden="true"> ↗</span>
                    </a>
                  </div>
                  <small>
                    {t(
                      "These are project validation checks, not official NISR classifications.",
                      "Ibi ni ibyavuye mu igenzura ry'umushinga, si ibyiciro byemejwe na NISR."
                    )}
                  </small>
                </div>
              </div>

              <div className="quality-stat-grid">
                <article className="quality-stat-card">
                  <span>{t("Total validation checks", "Igenzura ryose")}</span>
                  <strong>{fmt(filteredChecks.length)}</strong>
                  <small>{t("Crop and season comparisons", "Kugereranya ibihingwa n'ibihembwe")}</small>
                </article>
                <article className="quality-stat-card quality-stat-match">
                  <span>{t("Matches", "Imibare ihuye")}</span>
                  <strong>{fmt(filteredChecks.filter(c => c.validation_status === "MATCH").length)}</strong>
                  <small>{t("Figures agree under project rules", "Imibare ihuye hakurikijwe amategeko y'umushinga")}</small>
                </article>
                <article className="quality-stat-card quality-stat-review">
                  <span>{t("Small differences", "Itandukaniro rito")}</span>
                  <strong>{fmt(filteredChecks.filter(c => c.validation_status === "SMALL_DIFFERENCE_REVIEW").length)}</strong>
                  <small>{t("Require review", "Bikeneye gusuzumwa")}</small>
                </article>
                <article className="quality-stat-card quality-stat-incomplete">
                  <span>{t("Incomplete district data", "Amakuru y'uturere atuzuye")}</span>
                  <strong>{fmt(filteredChecks.filter(c => c.validation_status === "INCOMPLETE_DISTRICT_DATA").length)}</strong>
                  <small>{t("At least one district value is missing", "Nibura hari umubare w'akarere ubura")}</small>
                </article>
                <article className="quality-stat-card quality-stat-review">
                  <span>{t("Large differences", "Itandukaniro rinini")}</span>
                  <strong>{fmt(filteredChecks.filter(c => c.validation_status === "LARGE_DIFFERENCE_REVIEW").length)}</strong>
                  <small>{t("Require investigation", "Bikeneye iperereza")}</small>
                </article>
                <article className="quality-stat-card quality-stat-complete">
                  <span>{t("Complete district coverage", "Amakuru y'uturere yuzuye")}</span>
                  <strong>
                    {fmt(filteredChecks.filter(c => c.district_sum_completeness === "COMPLETE").length)}
                  </strong>
                  <small>
                    {t(
                      "All expected district values are present",
                      "Imibare y'uturere twose duteganyijwe irahari"
                    )}
                  </small>
                </article>
                <article className="quality-stat-card quality-stat-partial">
                  <span>{t("Partial district coverage", "Amakuru y'uturere atuzuye")}</span>
                  <strong>
                    {fmt(filteredChecks.filter(c => c.district_sum_completeness === "PARTIAL").length)}
                  </strong>
                  <small>
                    {t(
                      "At least one expected district value is missing",
                      "Nibura hari umubare w'akarere uteganyijwe ubura"
                    )}
                  </small>
                </article>
              </div>

              <ExplainThis
                en="A match means the district sum and published national figure agree under this project's validation rules. A difference is a reason to review the figures, not automatic proof that the source is wrong. Incomplete district data means the available district sum should not be treated as a complete national comparison. Missing values are never assumed to be zero."
                rwText="Imibare ihuye bivuga ko igiteranyo cy'uturere n'igiteranyo cy'igihugu byatangajwe bihuye hakurikijwe amategeko y'igenzura ry'umushinga. Itandukaniro risaba gusuzuma imibare, ariko ntihita ryemeza ko inyandiko y'inkomoko ifite amakosa. Amakuru y'uturere atuzuye asobanura ko igiteranyo gihari kidakwiye gufatwa nk'igereranya ryuzuye ry'igihugu. Imibare ibura ntifatwa nka zeru."
              />

              <article className="chart-card quality-records-card">
                <div className="card-heading">
                  <div>
                    <span className="section-kicker">
                      {t("VALIDATION REGISTER", "URUTONDE RW'IGENZURA")}
                    </span>
                    <h3>{t("Checks and source references", "Igenzura n'aho amakuru akomoka")}</h3>
                  </div>
                  <span className="quality-total">
                    {fmt(filteredChecks.length)} {t("checks", "by'igenzura")}
                  </span>
                </div>

                <p className="muted-copy">
                  {t(
                    "The district sum and published national total are shown separately. Source table and page numbers help you trace the figures in the report.",
                    "Igiteranyo cy'uturere n'igiteranyo cy'igihugu byatangajwe bigaragazwa ukwabyo. Imbonerahamwe n'urupapuro by'inkomoko bigufasha gusubira ku mibare iri muri raporo."
                  )}
                </p>

                <div className="quality-filters">
                  <label>
                    <span>{t("Season", "Igihembwe")}</span>
                    <select value={qualitySeason} onChange={e => setQualitySeason(e.target.value)}>
                      <option value="all">{t("All seasons", "Ibihembwe byose")}</option>
                      {qualitySeasons.map(value => (
                        <option key={value} value={value}>
                          {t(`Season ${value}`, `Igihembwe ${value}`)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label>
                    <span>{t("Crop", "Igihingwa")}</span>
                    <select value={qualityCrop} onChange={e => setQualityCrop(e.target.value)}>
                      <option value="all">{t("All crops", "Ibihingwa byose")}</option>
                      {qualityCrops.map(value => (
                        <option key={value} value={value}>{displayCropName(value)}</option>
                      ))}
                    </select>
                  </label>

                  <label>
                    <span>{t("Validation status", "Icyiciro cy'igenzura")}</span>
                    <select value={qualityStatus} onChange={e => setQualityStatus(e.target.value)}>
                      <option value="all">{t("All statuses", "Ibyiciro byose")}</option>
                      {qualityStatuses.map(value => (
                        <option key={value} value={value}>
                          {value === "MATCH"
                            ? t("Match", "Birahuye")
                            : value === "SMALL_DIFFERENCE_REVIEW"
                              ? t("Small difference — review", "Itandukaniro rito — genzura")
                              : value === "LARGE_DIFFERENCE_REVIEW"
                                ? t("Large difference — review", "Itandukaniro rinini — genzura")
                                : value === "INCOMPLETE_DISTRICT_DATA"
                                  ? t("Incomplete district data", "Amakuru y'uturere atuzuye")
                                  : value}
                        </option>
                      ))}
                    </select>
                  </label>

                  <button
                    type="button"
                    className="quality-reset-button"
                    onClick={() => {
                      setQualitySeason("all");
                      setQualityCrop("all");
                      setQualityStatus("all");
                    }}
                  >
                    {t("Reset filters", "Siba amahitamo")}
                  </button>
                </div>

                <p className="quality-filter-result" aria-live="polite">
                  {t(
                    `Showing ${filteredChecks.length} of ${checks.length} checks`,
                    `Hagaragajwe igenzura ${filteredChecks.length} kuri ${checks.length}`
                  )}
                </p>

                <div className="quality-record-list">
                  {filteredChecks.length === 0 ? (
                    <p className="quality-empty-state">
                      {t("No checks match these filters.", "Nta genzura rihuye n'aya mahitamo.")}
                    </p>
                  ) : filteredChecks.map((r, i) => {
                    const status = r.validation_status || "UNKNOWN";
                    const detailKey = `${r.year}-${r.season}-${r.crop}`;
                    const districtSearchTerm = (qualityDistrictSearch[detailKey] || "").trim().toLowerCase();
                    const matchingDistricts = (qualityDetails[detailKey]?.districts ?? []).filter((d) =>
                      String(d.district ?? "").toLowerCase().includes(districtSearchTerm)
                    );
                    const selectedDistrictIndex = qualityDistrictSearchIndex[detailKey] || 0;
                    const visibleDistricts = districtSearchTerm
                      ? matchingDistricts.slice(selectedDistrictIndex, selectedDistrictIndex + 1)
                      : (qualityDetails[detailKey]?.districts ?? []);

                    const districtDetail = qualityDetails[detailKey];
                    const statusClass = status === "MATCH"
                      ? "status-match"
                      : status === "INCOMPLETE_DISTRICT_DATA"
                        ? "status-incomplete"
                        : "status-review";
                    const statusLabel = status === "MATCH"
                      ? t("Match", "Birahuye")
                      : status === "INCOMPLETE_DISTRICT_DATA"
                        ? t("Incomplete district data", "Amakuru y'uturere atuzuye")
                        : status === "SMALL_DIFFERENCE_REVIEW"
                          ? t("Small difference — review", "Itandukaniro rito — genzura")
                          : status === "LARGE_DIFFERENCE_REVIEW"
                            ? t("Large difference — review", "Itandukaniro rinini — genzura")
                            : status;

                    const statusExplanation = status === "MATCH"
                      ? {
                          meaning: t(
                            "The district subtotal agrees with the published national figure under the project's validation rules.",
                            "Igiteranyo cy'uturere gihuye n'igiteranyo cy'igihugu cyatangajwe hakurikijwe amategeko y'igenzura ry'umushinga."
                          ),
                          action: t(
                            "Keep the source reference and check the original report when using this figure.",
                            "Bika aho amakuru yaturutse kandi urebe raporo y'umwimerere igihe ukoresha uyu mubare."
                          )
                        }
                      : status === "SMALL_DIFFERENCE_REVIEW"
                        ? {
                            meaning: t(
                              "A small difference exists between the district subtotal and the published national figure. It needs review; it does not automatically mean the source is wrong.",
                              "Hari itandukaniro rito hagati y'igiteranyo cy'uturere n'igiteranyo cy'igihugu cyatangajwe. Risaba gusuzumwa; ntibihita bivuga ko amakuru y'inkomoko ari amakosa."
                            ),
                            action: t(
                              "Compare the values, units, rounding, and source table in the original report.",
                              "Gereranya imibare, ibipimo, uko yazengurutswe n'imbonerahamwe y'inkomoko muri raporo y'umwimerere."
                            )
                          }
                        : status === "LARGE_DIFFERENCE_REVIEW"
                          ? {
                              meaning: t(
                                "The difference is large enough to require investigation before this comparison is relied on.",
                                "Itandukaniro rirahambaye ku buryo rigomba gukorwaho iperereza mbere yo kwishingikiriza kuri iri gereranya."
                              ),
                              action: t(
                                "Recheck the crop, season, units, district entries, and published source total. Do not assume which figure is wrong without evidence.",
                                "Ongera urebe igihingwa, igihembwe, ibipimo, imibare y'uturere n'igiteranyo cyatangajwe. Ntukemeze ko umubare runaka ari amakosa utabifitiye ibimenyetso."
                              )
                            }
                          : status === "INCOMPLETE_DISTRICT_DATA"
                            ? {
                                meaning: t(
                                  "One or more expected district values are missing, so the available subtotal is not a complete district-based national comparison.",
                                  "Umubare w'akarere kamwe cyangwa menshi uteganyijwe urabura, bityo igiteranyo gihari ntigishobora gufatwa nk'igereranya ryuzuye ry'igihugu rishingiye ku turere."
                                ),
                                action: t(
                                  "Check the missing district values and source notes. Missing values are not zero; avoid conclusions based on an incomplete subtotal.",
                                  "Reba imibare y'uturere ibura n'ibisobanuro by'inkomoko. Imibare ibura si zeru; irinde gufata imyanzuro ushingiye ku giteranyo kituzuye."
                                )
                              }
                            : {
                                meaning: t(
                                  "This record has an unrecognized validation status, so its meaning has not been established here.",
                                  "Iyi nyandiko ifite icyiciro cy'igenzura kitazwi, bityo ibisobanuro byacyo ntibiramenyekana hano."
                                ),
                                action: t(
                                  "Check the source record and validation rules before interpreting this result.",
                                  "Reba inyandiko y'inkomoko n'amategeko y'igenzura mbere yo gusobanura iki gisubizo."
                                )
                              };

                    return (
                      <div className="quality-record" key={`${r.year}-${r.season}-${r.crop}-${i}`}>
                        <div className="quality-record-heading">
                          <div>
                            <b>{displayCropName(r.crop)}</b>
                            <small>{t("Season", "Igihembwe")} {r.season} · {r.year}</small>
                          </div>
                          <span className={`validation-status ${statusClass}`}>
                            {statusLabel}
                          </span>
                        </div>

                        <div className="quality-record-metrics">
                          <div>
                            <small>{t("District subtotal", "Igiteranyo cy'uturere")}</small>
                            <strong>
                              {r.district_sum_mt == null ? "—" : `${fmt(number(r.district_sum_mt))} MT`}
                            </strong>
                          </div>
                          <div>
                            <small>{t("Published national total", "Igiteranyo cy'igihugu cyatangajwe")}</small>
                            <strong>
                              {r.published_national_mt == null ? "—" : `${fmt(number(r.published_national_mt))} MT`}
                            </strong>
                          </div>
                          <div>
                            <small>{t("Difference", "Itandukaniro")}</small>
                            <strong>
                              {r.difference_mt == null ? t("Not compared", "Ntabwo byagereranyijwe") : `${fmt(number(r.difference_mt))} MT`}
                            </strong>
                          </div>
                        </div>

                        <div className="quality-source-reference">
                          <span>
                            {t("Source table", "Imbonerahamwe y'inkomoko")} {r.source_table ?? "—"}
                          </span>
                          <span>
                            {t("Page", "Urupapuro")} {r.source_page ?? "—"}
                          </span>
                          <span>
                            {t("Missing districts", "Uturere tutatanze amakuru")}: {r.district_missing_count ?? "—"}
                          </span>
                        </div>

                        <div className={`quality-interpretation ${statusClass}`}>
                          <div>
                            <b>{t("What this means", "Icyo bivuze")}</b>
                            <p>{statusExplanation.meaning}</p>
                          </div>
                          <div>
                            <b>{t("Recommended next step", "Intambwe ikurikira")}</b>
                            <p>{statusExplanation.action}</p>
                          </div>
                        </div>

                        <button
                          type="button"
                          className="quality-detail-toggle"
                          aria-expanded={qualityDetailOpen === detailKey}
                          onClick={() => toggleQualityDetails(r)}
                        >
                          {qualityDetailOpen === detailKey
                            ? t("Hide district details", "Hisha amakuru y'uturere")
                            : t("View district details", "Reba amakuru y'uturere")}
                          <span aria-hidden="true">
                            {qualityDetailOpen === detailKey ? "−" : "+"}
                          </span>
                        </button>

                        {qualityDetailOpen === detailKey && (
                          <section className="quality-district-details">
                            {qualityDetailLoading[detailKey] && (
                              <p role="status">
                                {t(
                                  "Loading district records…",
                                  "Amakuru y'uturere arimo gufungurwa…"
                                )}
                              </p>
                            )}

                            {qualityDetailErrors[detailKey] && (
                              <div className="quality-detail-error" role="alert">
                                <p>
                                  {t(
                                    "District details could not be loaded. Check the API connection and try again.",
                                    "Amakuru y'uturere ntiyabashije kuboneka. Reba ko API ikora, wongere ugerageze."
                                  )}
                                </p>
                                <button
                                  type="button"
                                  className="quality-detail-retry"
                                  onClick={() => {
                                    setQualityDetails(previous => {
                                      const next = { ...previous };
                                      delete next[detailKey];
                                      return next;
                                    });
                                    toggleQualityDetails(r, true);
                                  }}
                                >
                                  {t("Retry", "Ongera ugerageze")}
                                </button>
                              </div>
                            )}

                            {districtDetail && (
                              <>
                                <h4>
                                  {t("District-level investigation", "Iperereza ku rwego rw'uturere")}
                                </h4>
                                <p className="quality-district-note">
                                  {t(
                                    "Historical crop-production figures for this season—not current food stocks or market availability.",
                                    "Imibare y'umusaruro w'igihingwa yo muri iki gihembwe cyashize—si ibiribwa bihari ubu cyangwa ibyo ku isoko."
                                  )}
                                </p>

                                <div className="quality-district-summary">
                                  <div>
                                    <small>{t("Reported districts", "Uturere twatanze imibare")}</small>
                                    <strong>
                                      {districtDetail.summary?.reported_records ?? "—"}
                                    </strong>
                                  </div>
                                  <div>
                                    <small>{t("District records", "Inyandiko z'uturere")}</small>
                                    <strong>
                                      {districtDetail.summary?.district_records ?? "—"}
                                    </strong>
                                  </div>
                                  <div>
                                    <small>{t("Coverage", "Ubuzure bw'amakuru")}</small>
                                    <strong>
                                      {districtDetail.summary?.district_coverage_percent == null
                                        ? "—"
                                        : `${fmt(number(districtDetail.summary.district_coverage_percent))}%`}
                                    </strong>
                                  </div>
                                  <div>
                                    <small>{t("Missing values", "Imibare ibura")}</small>
                                    <strong>
                                      {districtDetail.summary?.missing_production_records ?? "—"}
                                    </strong>
                                  </div>
                                </div>

                                <input
                                  className="quality-district-search"
                                  type="text"
                                  placeholder={t("Search district...", "Shaka akarere...")}
                                  value={qualityDistrictSearch[detailKey] || ""}
                                  onChange={(event) => {
                                    setQualityDistrictSearch((previous) => ({
                                      ...previous,
                                      [detailKey]: event.target.value,
                                    }));
                                    setQualityDistrictSearchIndex((previous) => ({
                                      ...previous,
                                      [detailKey]: 0,
                                    }));
                                  }}
                                  aria-label={t("Search district", "Shaka akarere")}
                                />

                                {districtSearchTerm && (
                                  <div className="quality-district-search-controls">
                                    <span className="quality-district-search-count" aria-live="polite">
                                      {matchingDistricts.length === 0
                                        ? t("No districts found", "Nta karere kabonetse")
                                        : `${t("Result", "Igisubizo")} ${selectedDistrictIndex + 1} ${t("of", "kuri")} ${matchingDistricts.length}`}
                                    </span>
                                    <div className="quality-district-search-actions">
                                      <button
                                        type="button"
                                        className="quality-district-nav"
                                        onClick={() => setQualityDistrictSearchIndex((previous) => ({
                                          ...previous,
                                          [detailKey]: Math.max(0, selectedDistrictIndex - 1),
                                        }))}
                                        disabled={matchingDistricts.length === 0 || selectedDistrictIndex <= 0}
                                      >
                                        {t("Previous", "Ibanjirije")}
                                      </button>
                                      <button
                                        type="button"
                                        className="quality-district-nav"
                                        onClick={() => setQualityDistrictSearchIndex((previous) => ({
                                          ...previous,
                                          [detailKey]: Math.min(matchingDistricts.length - 1, selectedDistrictIndex + 1),
                                        }))}
                                        disabled={matchingDistricts.length === 0 || selectedDistrictIndex >= matchingDistricts.length - 1}
                                      >
                                        {t("Next", "Ikurikira")}
                                      </button>
                                      <button
                                        type="button"
                                        className="quality-district-nav quality-district-clear"
                                        onClick={() => {
                                          setQualityDistrictSearch((previous) => ({
                                            ...previous,
                                            [detailKey]: "",
                                          }));
                                          setQualityDistrictSearchIndex((previous) => ({
                                            ...previous,
                                            [detailKey]: 0,
                                          }));
                                        }}
                                      >
                                        {t("Clear search", "Siba ishakisha")}
                                      </button>
                                    </div>
                                  </div>
                                )}
                                {districtSearchTerm && matchingDistricts.length === 0 && (
                                  <p className="quality-district-no-results">
                                    {t("Try another district name.", "Gerageza izina ry'akarere.")
                                    }
                                  </p>
                                )}

                                <div className="quality-district-table-wrap">
                                  <table className="quality-district-table">
                                    <thead>
                                      <tr>
                                        <th>{t("Rank", "Urutonde")}</th>
                                        <th>{t("District", "Akarere")}</th>
                                        <th>{t("Production (MT)", "Umusaruro (MT)")}</th>
                                        <th>{t("Reporting status", "Imiterere y'amakuru")}</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {visibleDistricts.map((d, districtIndex) => (
                                        <tr
                                          key={`${d.district}-${districtIndex}`}
                                          className={districtSearchTerm ? "quality-district-selected" : undefined}
                                        >
                                          <td>{d.rank ?? "—"}</td>
                                          <td>{d.district || "—"}</td>
                                          <td>
                                            {d.production_mt == null
                                              ? "—"
                                              : fmt(number(d.production_mt))}
                                          </td>
                                          <td>
                                            <span className={
                                              d.production_mt == null
                                                ? "quality-value-missing"
                                                : "quality-value-reported"
                                            }>
                                              {d.production_mt == null
                                                ? t("Not reported", "Ntabwo yatanzwe")
                                                : t("Reported", "Yatanzwe")}
                                            </span>
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>

                                <button
                                  type="button"
                                  className="quality-district-export"
                                  onClick={() => {
                                    const districts = districtDetail.districts ?? [];
                                    const headers = [
                                      "Crop",
                                      "Season",
                                      "Year",
                                      "District",
                                      "Rank",
                                      "Production (MT)",
                                      "Reporting status",
                                      "Source table",
                                      "Source page",
                                      "Interpretation",
                                    ];
                                    const csvCell = (value) =>
                                      `"${String(value ?? "").replace(/"/g, '""')}"`;
                                    const rows = districts.map((d) => [
                                      r.crop,
                                      r.season,
                                      r.year,
                                      d.district ?? "",
                                      d.rank ?? "",
                                      d.production_mt ?? "",
                                      d.production_mt == null ? "Not reported" : "Reported",
                                      r.source_table ?? "",
                                      r.source_page ?? "",
                                      "Historical survey production; not current food stocks or market availability",
                                    ]);
                                    const csv = "\uFEFF" + [headers, ...rows]
                                      .map((row) => row.map(csvCell).join(","))
                                      .join("\r\n");
                                    const blob = new Blob([csv], {
                                      type: "text/csv;charset=utf-8;",
                                    });
                                    const url = URL.createObjectURL(blob);
                                    const link = document.createElement("a");
                                    const safeCrop = String(r.crop ?? "crop")
                                      .replace(/[^a-z0-9]+/gi, "-")
                                      .replace(/^-|-$/g, "");
                                    link.href = url;
                                    link.download = `menya-neza-${safeCrop}-${r.season}-${r.year}-districts.csv`;
                                    document.body.appendChild(link);
                                    link.click();
                                    link.remove();
                                    URL.revokeObjectURL(url);
                                  }}
                                  disabled={(districtDetail.districts ?? []).length === 0}
                                >
                                  {t("Download CSV", "Kuramo CSV")}
                                </button>

                                <div className="quality-citation-actions">
                  <button
                    type="button"
                    className="quality-citation-copy"
                    onClick={async () => {
                      const citation = [
                        "National Institute of Statistics of Rwanda (NISR).",
                        "Seasonal Agricultural Survey 2025.",
                        `Table ${r.source_table ?? "—"}, page ${r.source_page ?? "—"}.`,
                        `Crop: ${r.crop}; season: ${r.season}; year: ${r.year}.`,
                        "MENYA NEZA AI data-quality reference.",
                        "Historical survey production; not current food stocks or market availability."
                      ].join(" ");
                      try {
                        if (!navigator.clipboard?.writeText) {
                          throw new Error("Clipboard API unavailable");
                        }
                        await navigator.clipboard.writeText(citation);
                        setQualityCitationStatus("copied");
                      } catch {
                        setQualityCitationStatus("error");
                      }
                    }}
                  >
                    {qualityCitationStatus === "copied"
                      ? t("Citation copied!", "Amakuru y'inkomoko yakoporowe!")
                      : t("Copy source citation", "Koporora inkomoko y'amakuru")}
                  </button>
                  {qualityCitationStatus === "error" && (
                    <span className="quality-citation-feedback" role="status">
                      {t("Copy unavailable. Try using the site in a secure browser context.", "Gukoporora ntibyashobotse. Gerageza gukoresha urubuga muri browser irinzwe.")}
                    </span>
                  )}
                </div>
                <p className="quality-district-source">
                                  {t("Source table", "Imbonerahamwe y'inkomoko")}{" "}
                                  {r.source_table ?? "—"} · {t("Page", "Urupapuro")}{" "}
                                  {r.source_page ?? "—"}
                                </p>

                                <p className="quality-district-note">
                                  {t(
                                    "A dash means the value was not reported; it does not mean zero. Rankings include only districts with numeric values.",
                                    "Umurongo (—) ugaragaza ko umubare utatanzwe; ntibivuga zeru. Urutonde rushingira gusa ku turere dufite imibare."
                                  )}
                                </p>
                              </>
                            )}
                          </section>
                        )}
                      </div>
                    );
                  })}
                </div>
              </article>

              <div className="quality-caveat">
                <b>{t("Important limitation", "Icyitonderwa cy'ingenzi")}</b>
                <p>
                  {t(
                    "These checks describe the quality and completeness of historical survey figures. They do not measure current food stocks, market availability, crop success, or live disaster risk. Use the original NISR report for context before making decisions.",
                    "Iri genzura risobanura ubwiza n'ubuzure bw'imibare y'ubushakashatsi bwo mu bihe byashize. Ntirigaragaza ibiribwa bihari ubu, ibiboneka ku masoko, uko umusaruro wagenze cyangwa ibyago by'ibiza biriho ubu. Banza urebe raporo y'umwimerere ya NISR kugira ngo ubone ibisobanuro bihagije mbere yo gufata ibyemezo."
                  )}
                </p>
              </div>
            </>
          )}
        </main>
      )}

      {page === "intelligence" && (
        <main className="inner-page">
          <button className="back-link" onClick={() => navigate("home")}>
            ← {t("Back to home", "Garuka ku ntangiriro")}
          </button>

          <div className="inner-heading">
            <span className="section-kicker">
              {t("EVIDENCE BEFORE ESTIMATES", "IBIMENYETSO MBERE Y'IGERERANYA")}
            </span>
            <h1>{t("Market Intelligence: How Production Connects to Prices", "Isesengura ry'amasoko: Uburyo umusaruro ufitanye isano n'ibiciro")}</h1>
            <div className="intelligence-intro">
              <p>{t(
                "Two sources. Different questions. Evidence you can examine.",
                "Inkomoko ebyiri. Ibibazo bitandukanye. Ibimenyetso ushobora gusuzuma."
              )}</p>
              <p>{t(
                "Historical NISR crop production shows what was harvested. TangaBid monthly price summaries show reported price patterns. Together, they offer complementary perspectives on agriculture and markets but they do not establish that production changes caused price changes.",
                "Imibare ya NISR yo mu bihe byashize igaragaza umusaruro wasaruwe. Incamake z'ibiciro bya buri kwezi za TangaBid zigaragaza uko ibiciro byagiye bihinduka. Bifatanije, bitanga amakuru yuzuzanya ku buhinzi no ku masoko, ariko ntibyemeza ko ihinduka ry'umusaruro ari ryo ryateye ihinduka ry'ibiciro."
              )}</p>
            </div>
          </div>

          <div className="explorer-card">
            <div className="explorer-controls">
              <label>{t("Crop", "Igihingwa")}
                <select value={intelCrop} onChange={e => setIntelCrop(e.target.value)}>
                  {[...new Set(["Maize", ...records.map(r => r.crop).filter(Boolean)])]
                    .sort((a, b) => a.localeCompare(b))
                    .map(crop => (
                      <option key={crop} value={crop}>{displayCropName(crop)}</option>
                    ))}
                </select>
              </label>

              <label>{t("Season", "Igihembwe")}
                <select value={intelSeason} onChange={e => setIntelSeason(e.target.value)}>
                  {Object.entries(seasons).map(([key, period]) => (
                    <option key={key} value={key}>
                      {t("Season", "Igihembwe")} {key} · {period}
                    </option>
                  ))}
                </select>
              </label>

              <label>{t("District", "Akarere")}
                <select value={district} onChange={e => setDistrict(e.target.value)}>
                  {districts.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </label>
            </div>

            <div className="data-context">
              <span className="context-icon">i</span>
              {t(
                "Reference period: 2025 · NISR Seasonal Agricultural Survey",
                "Igihe cy'amakuru: 2025 · Ubushakashatsi bwa NISR ku buhinzi"
              )}
            </div>
          </div>

          {intelLoading && (
            <div className="state-panel">
              {t("Loading evidence…", "Amakuru arimo gutegurwa…")}
            </div>
          )}

          {intelError && (
            <div className="state-panel error-panel">
              {t(
                "Could not load intelligence. Check that the backend is running, then try again.",
                "Amakuru ntiyabashije kuboneka. Reba niba backend iri gukora, wongere ugerageze."
              )}
            </div>
          )}

          {!intelLoading && !intelError && intelReport && (
            <>
              <div className="area-summary">
                <div>
                  <span>{t("SELECTED EVIDENCE", "AMAKURU YATORANYIJWE")}</span>
                  <h2>{displayCropName(intelReport.filters.crop)} · {district}</h2>
                  <small>
                    {t("Season", "Igihembwe")} {intelReport.filters.season}
                    {" · "}{intelReport.filters.season_period}
                  </small>
                </div>
                <div className="history-badge">
                  <span /> {t("HISTORICAL DATA", "AMAKURU YO MU BIHE BYASHIZE")}
                </div>
              </div>

              <div className="stat-grid">
                <article className="stat-card stat-primary">
                  <span className="stat-label">
                    {t("Reported district production", "Umusaruro watangajwe mu karere")}
                  </span>
                  <strong>
                    {intelReport.selected_district_evidence?.production_mt == null
                      ? "—"
                      : `${fmt(intelReport.selected_district_evidence.production_mt)} MT`}
                  </strong>
                  <p>{t(
                    "Historical production, not current market stock.",
                    "Umusaruro wo mu bihe byashize; ntugaragaza umusaruro ubitswe ku isoko ubu."
                  )}</p>
                </article>

                <article className="stat-card">
                  <span className="stat-label">
                    {t("District reporting coverage", "Igipimo cy'uturere twatanze amakuru")}
                  </span>
                  <strong>
                    {intelReport.production_evidence?.district_coverage_percent == null
                      ? "—"
                      : fmt(intelReport.production_evidence.district_coverage_percent)}
                    {intelReport.production_evidence?.district_coverage_percent != null && (
                      <small>%</small>
                    )}
                  </strong>
                  <p>
                    {intelReport.production_evidence?.reported_records ?? "—"}
                    {" / "}
                    {intelReport.production_evidence?.summary?.expected_districts_in_dataset ?? "—"}
                    {" "}{t("districts with reported production", "uturere bifite imibare y'umusaruro yatanzwe")}
                  </p>
                  <p className="stat-note">
                    {t(
                      "Coverage measures districts with numeric production records; it does not measure current food availability.",
                      "Iki gipimo kigaragaza uturere dufite imibare y'umusaruro; ntikigaragaza ibiribwa bihari ku isoko ubu."
                    )}
                  </p>
                </article>

                <article className="stat-card">
                  <span className="stat-label">
                    {t("Verified price observations", "Ibipimo by'ibiciro byagenzuwe")}
                  </span>
                  <strong>
                    {intelReport.market_price_intelligence?.price_observations?.length ?? 0}
                  </strong>
                  <p>{t(
                    "No verified price feed is connected; no price trend or forecast is produced.",
                    "Nta nkomoko y'amakuru y'ibiciro yagenzuwe ihujwe; bityo nta mpinduka z'ibiciro cyangwa iteganyabiciro bitangwa hano."
                  )}</p>
                </article>
              </div>

              {intelReport.situation_summary && (
                <article className="chart-card">
                  <div className="card-heading">
                    <div>
                      <span className="section-kicker">
                        {t("CONNECTED EVIDENCE", "AMAKURU AHURIYE HAMWE")}
                      </span>
                      <h3>
                        {t("Situation summary", "Incamake y'uko ibintu bihagaze")}
                      </h3>
                    </div>
                    <span className="unit-label">
                      {intelReport.situation_summary.status === "HISTORICAL_EVIDENCE_AVAILABLE"
                        ? t("EVIDENCE FOUND", "AMAKURU YABONETSE")
                        : t("LIMITED", "MAKE")}
                    </span>
                  </div>

                  <p>
                    {intelReport.situation_summary.status === "HISTORICAL_EVIDENCE_AVAILABLE"
                      ? t(
                          "Historical production evidence is available for this selection. It is not a live food-security or disaster-risk assessment.",
                          "Hari imibare y'umusaruro wo mu bihe byashize ijyanye n'ibyo wahisemo. Ntabwo ari isuzuma ry'umutekano w'ibiribwa cyangwa ibyago by'ibiza biriho ubu."
                        )
                      : t(
                          "There is not enough matching historical evidence for a reliable assessment.",
                          "Nta makuru ahagije yo mu bihe byashize ahuye n'ibyo wahisemo kugira ngo habe isuzuma ryizewe."
                        )}
                  </p>

                  <div className="plain-note">
                    <span className="note-icon">i</span>
                    <div>
                      <b>{t("What the data shows", "Ibyo amakuru agaragaza")}</b>
                      <p>
                        {t("Selected district", "Akarere wahisemo")}:{" "}
                        {intelReport.situation_summary.observed?.selected_district_production_mt == null
                          ? t("No numeric observation available", "Nta mubare w'umusaruro uhari")
                          : `${fmt(intelReport.situation_summary.observed.selected_district_production_mt)} MT`}
                        {" · "}
                        {t("Reporting coverage", "Igipimo cy'amakuru yatanzwe")}:{" "}
                        {intelReport.situation_summary.observed?.district_coverage_percent == null
                          ? "—"
                          : `${fmt(intelReport.situation_summary.observed.district_coverage_percent)}%`}
                        {" · "}
                        {t("Validation", "Igenzura")}:{" "}
                        {intelReport.situation_summary.observed?.validation_status || "—"}
                      </p>
                    </div>
                  </div>

                  <div className="plain-note">
                    <span className="note-icon">?</span>
                    <div>
                      <b>{t("What remains unknown", "Ibitaramenyekana")}</b>
                      <ul>
                        {(intelReport.situation_summary.unknowns || []).map((item, index) => (
                          <li key={item}>
                            {t(item, [
                              "Imibare y'umusaruro wo mu bihe byashize ntigaragaza ububiko bw'ibiribwa cyangwa ibiboneka ku isoko ubu.",
                              "Nta bipimo by'ibiciro byagenzuwe bihujwe n'iyi raporo.",
                              "Iyi raporo ntibarura cyangwa ngo yemeze ibyago by'ibiza biriho ubu."
                            ][index] || item)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="plain-note">
                    <span className="note-icon">→</span>
                    <div>
                      <b>{t("Recommended next actions", "Intambwe zikurikiraho")}</b>
                      <ul>
                        {(intelReport.situation_summary.recommended_next_actions || []).map((item, index) => (
                          <li key={item}>
                            {t(item, [
                              "Suzuma uko amakuru yatanzwe yuzuye n'uko igenzura ry'igihembwe wahisemo ryagenze.",
                              "Reba inkomoko y'imibare y'uturere ituzuye mbere yo gusobanura igiteranyo.",
                              "Huza ibipimo by'ibiciro bifite amatariki n'inkomoko byagenzuwe mbere yo gusuzuma ihinduka ry'ibiciro.",
                              "Koresha amakuru y'ikirere cyangwa ibyago by'ibiza yagenzuwe n'uburyo bwemejwe mbere yo gutanga umuburo."
                            ][index] || item)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <p className="chart-footnote">
                    {t(
                      "This is an evidence summary, not a live risk score or forecast. Missing values remain unknown, not zero.",
                      "Iyi ni incamake y'ibimenyetso, si amanota y'ibyago biriho ubu cyangwa iteganyagihe. Imibare ibura ifatwa nk'itabonetse, ntabwo ari zeru."
                    )}
                  </p>
                </article>
              )}

              <div className="data-layout">
                <article className="chart-card">
                  <div className="card-heading">
                    <div>
                      <span className="section-kicker">
                        {t("PRODUCTION EVIDENCE", "IBIMENYETSO BY'UMUSARURO")}
                      </span>
                      <h3>{t("Leading reported districts", "Uturere twagaragaje umusaruro mwinshi")}</h3>
                    </div>
                    <span className="unit-label">MT</span>
                  </div>

                  {(intelReport.production_evidence?.supply_origins?.leading_reported_districts || []).length
                    ? <div className="bar-chart">
                        {intelReport.production_evidence.supply_origins.leading_reported_districts.map((item, index, list) => {
                          const maxValue = Math.max(...list.map(d => d.production_mt || 0), 1);
                          return (
                            <div className="bar-row" key={item.district}>
                              <div className="bar-title">
                                <span>{item.rank}. {item.district}</span>
                                <b>{fmt(item.production_mt)} MT</b>
                              </div>
                              <div className="bar-track">
                                <span
                                  className={index === 0 ? "bar-fill bar-fill-main" : "bar-fill"}
                                  style={{ width: `${Math.max(1.5, item.production_mt / maxValue * 100)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    : <p className="empty-state">
                        {t("No reported district values are available.", "Nta mibare y'uturere yatanzwe iboneka.")}
                      </p>}

                  <p className="chart-footnote">{t(
                    "Source: NISR Seasonal Agricultural Survey 2025. These historical figures do not establish current stocks, retail availability, or household food security.",
                    "Inkomoko: NISR Seasonal Agricultural Survey 2025. Iyi mibare yo mu bihe byashize ntigaragaza ububiko buriho ubu, ibicuruzwa biri ku isoko cyangwa umutekano w'ibiribwa mu ngo."
                  )}</p>
                </article>

                <aside className="insight-column">
                  <article className="insight-card">
                    <span className="section-kicker">
                      {t("PRICE DATA STATUS", "IMITERERE Y'AMAKURU Y'IBICIRO")}
                    </span>
                    <h3>{t("No verified prices connected", "Nta biciro byagenzuwe bihari")}</h3>
                    <strong>{t("Research needed", "Haracyakenewe ubushakashatsi")}</strong>
                    <p>{t(
                      "Source registry entries are research leads, not price observations. A published price needs a verified value, unit, price type, location, date, source, and quality checks.",
                      "Aho amakuru y'ibiciro ashobora kuboneka ni ahantu ho gukomeza ubushakashatsi, si ibiciro byabonetse. Igiciro gitangazwa kigomba kugira agaciro kagenzuwe, igipimo, ubwoko bw'igiciro, ahantu, itariki, inkomoko n'igenzura ry'ubwiza."
                    )}</p>
                  </article>

                  <article className="plain-note">
                    <span className="note-icon">i</span>
                    <div>
                      <b>{t("Validation status", "Imiterere y'igenzura")}</b>
                      <p>
                        {intelReport.production_evidence?.summary?.validation_status || "NOT_AVAILABLE"}
                        {" · "}{t(
                          "The district subtotal can differ from the published national figure. Review the source validation before interpreting it.",
                          "Igiteranyo cy'uturere gishobora gutandukana n'umubare watangajwe ku rwego rw'igihugu. Banza urebe igenzura ry'inkomoko."
                        )}
                      </p>
                    </div>
                  </article>

                  <article className="data-warning">
                    <span className="warning-icon">!</span>
                    <div>
                      <b>{t("No price forecast", "Nta iteganyabiciro")}</b>
                      <p>{t(
                        "Production alone cannot show whether prices will rise or fall. Comparable, dated price observations are required.",
                        "Umusaruro wonyine ntugaragaza niba ibiciro bizazamuka cyangwa bizagabanuka. Hakenewe ibiciro byabonetse mu bihe bitandukanye kandi bifite amatariki."
                      )}</p>
                    </div>
                  </article>
                </aside>
              </div>
            </>
          )}
          <section className="price-trends-section" aria-labelledby="price-trends-title">
            <div className="price-trends-heading">
              <span className="section-kicker">
                {t("SOURCE-PROVIDED PRICE SUMMARIES", "IBICIRO BYATANZWE N'INKOMOKO")}
              </span>
              <h2 id="price-trends-title">
                {t("Explore market price trends", "Reba imiterere y'ibiciro ku masoko")}
              </h2>
              <p>
                {t(
                  "Browse monthly summaries supplied in the TangaBid dataset for April–October 2026 (seven calendar months; October may be incomplete). These records are separate from the NISR crop-production figures above.",
                  "Reba incamake y'ibiciro bya buri kwezi yatanzwe na TangaBid kuva muri Mata kugeza Ukwakira 2026 (amezi arindwi; amakuru yo mu Ukwakira ashobora kuba atuzuye). Aya makuru atandukanye n'imibare y'umusaruro wa NISR iri hejuru."
                )}
              </p>
            </div>

            <div className="price-trends-notice" role="note">
              <strong>{t("Important data limitations", "Imipaka y'aya makuru")}</strong>
              <p>
                {t(
                  "Currency, collection method, and exact price type have not been independently verified. These are not live prices or forecasts. October 2026 may be incomplete. Sample counts are reported by the source, and their meaning still needs confirmation. Consistency of markets, sellers, and sampling methods across months is also unverified, so apparent changes may partly reflect changes in the sampled records.",
                  "Ifaranga, uburyo bwo gukusanya amakuru n'ubwoko nyabwo bw'ibiciro ntibiragenzurwa n'undi muntu wigenga. Aya si amakuru y'ibiciro yo muri aka kanya cyangwa iteganyabiciro. Amakuru yo mu Ukwakira 2026 ashobora kuba atuzuye. Umubare w'ibipimo watanzwe n'inkomoko, ariko ibisobanuro byawo biracyakeneye kwemezwa. Ntabwo kandi hagenzuwe niba amasoko, abagurisha n'uburyo bwo gufata ibipimo byakoreshejwe mu mezi yose byari bimwe; bityo impinduka zigaragara zishobora guterwa n'impinduka mu makuru yakusanyijwe."
                )}
              </p>
            </div>

            <div className="price-trends-filters">
              {[
                { key: "product", label: t("Product", "Igicuruzwa"), optionKey: "products" },
                { key: "month", label: t("Month", "Ukwezi"), optionKey: "months" },
                { key: "region", label: t("Region", "Intara"), optionKey: "regions" },
                { key: "location", label: t("Location", "Ahantu"), optionKey: "locations" },
                { key: "unit", label: t("Unit", "Igipimo"), optionKey: "units" },
              ].map(filter => (
                <label key={filter.key}>
                  {filter.label}
                  <select
                    value={priceFilters[filter.key]}
                    onChange={event => {
                      const value = event.target.value;
                      setPriceFilters(previous => ({
                        ...previous,
                        [filter.key]: value,
                      }));
                      setPriceOffset(0);
                    }}
                  >
                    <option value="">{t("All", "Byose")}</option>
                    {(priceData?.available_options?.[filter.optionKey] || []).map(option => (
                      <option key={option} value={option}>
                        {filter.key === "month"
                          ? new Date(`${option}T12:00:00`).toLocaleDateString(
                              rw ? "rw-RW" : "en-US",
                              { month: "long", year: "numeric" }
                            )
                          : option}
                      </option>
                    ))}
                  </select>
                </label>
              ))}

              <button
                type="button"
                className="price-trends-reset"
                onClick={() => {
                  setPriceFilters({
                    product: "",
                    month: "",
                    region: "",
                    location: "",
                    unit: "",
                  });
                  setPriceOffset(0);
                }}
              >
                {t("Reset filters", "Siba amayungurura")}
              </button>
            </div>


            <div className="monthly-trend-panel">
              <div className="monthly-trend-heading">
                <div>
                  <span className="section-kicker">
                    {t("MONTHLY HISTORY", "AMATEKA Y'IBICIRO BYA BURI KWEZI")}
                  </span>
                  <h3>{t("Reported price range by month", "Ibiciro byatanzwe buri kwezi")}</h3>
                  <p>
                    {t(
                      "The line shows the source-reported average; vertical ranges show reported minimum and maximum values. This chart shows the available history and is not narrowed by the Month filter, which applies to the table below.",
                      "Umurongo werekana impuzandengo yatanzwe; imirongo ihagaze igaragaza ibiciro byo hasi n'ibyo hejuru. Iyi shusho igaragaza amateka y'ibiciro ahari; ntigabanywa n'ukwezi wahisemo, kuko akayunguruzo k'ukwezi gakoreshwa ku mbonerahamwe iri hepfo."
                    )}
                  </p>
                </div>
                <span className="monthly-trend-unit">{priceFilters.unit || "—"}</span>
              </div>

              {!priceFilters.product || !priceFilters.unit || !priceFilters.location ? (
                <div className="price-trends-empty">
                  {t(
                    "Select a product, unit, and location above to view its monthly history.",
                    "Hitamo igicuruzwa, igipimo n'ahantu hejuru kugira ngo ubone amateka y'ibiciro."
                  )}
                </div>
              ) : trendLoading ? (
                <div className="price-trends-state" role="status">
                  {t("Loading complete monthly history…", "Amateka yose y'ibiciro arimo kuzanwa…")}
                </div>
              ) : trendError ? (
                <div className="price-trends-state price-trends-error" role="alert">
                  {t(
                    "The monthly chart could not be loaded. Use Retry to try again.",
                    "Imbonerahamwe y'ibiciro ntiyabashije kuboneka. Kanda Ongera ugerageze."
                  )}
                  <button
                    type="button"
                    onClick={() => setPriceRefresh(value => value + 1)}
                  >
                    {t("Retry", "Ongera ugerageze")}
                  </button>
                </div>
              ) : trendData && trendData.records.length > 0 ? (
                (() => {
                  const records = [...trendData.records].sort(
                    (a, b) => a.month.localeCompare(b.month)
                  );
                  const low = Math.min(...records.map(row => Number(row.min_price)));
                  const high = Math.max(...records.map(row => Number(row.max_price)));
                  const span = high - low || 1;
                  const x = index => records.length === 1
                    ? 380
                    : 56 + index * (648 / (records.length - 1));
                  const y = value => 220 - ((Number(value) - low) / span) * 170;
                  const barWidth = Math.min(
                    24,
                    (648 / Math.max(records.length, 1)) * 0.55
                  );

                  return (
                    <>
                      <div className="monthly-trend-legend">
                        <span><i className="trend-legend-average" />{t("Reported average", "Impuzandengo yatanzwe")}</span>
                        <span><i className="trend-legend-range" />{t("Minimum–maximum range", "Igiciro cyo hasi n'icyo hejuru")}</span>
                      </div>
                      <div className="monthly-trend-chart-wrap">
                        <svg
                          className="monthly-trend-chart"
                          viewBox="0 0 760 285"
                          role="img"
                          aria-label={t(
                            `Monthly reported price history for ${priceFilters.product}, ${priceFilters.unit}, ${priceFilters.location}`,
                            `Amateka y'ibiciro bya ${priceFilters.product}, ${priceFilters.unit}, ${priceFilters.location}`
                          )}
                        >
                          {[0, 1, 2, 3].map(tick => {
                            const value = high - (span * tick / 3);
                            const yy = 30 + tick * (190 / 3);
                            return (
                              <g key={tick}>
                                <line x1="48" y1={yy} x2="730" y2={yy} className="trend-grid-line" />
                                <text x="40" y={yy + 4} textAnchor="end" className="trend-axis-label">
                                  {value.toLocaleString("en-US", { maximumFractionDigits: 2 })}
                                </text>
                              </g>
                            );
                          })}
                          {records.map((row, index) => (
                            <rect
                              key={`avg-bar-${row.month}-${row.location}`}
                              x={x(index) - barWidth / 2}
                              y={y(row.avg_price)}
                              width={barWidth}
                              height={Math.max(0, 220 - y(row.avg_price))}
                              rx="4"
                              className="trend-average-bar"
                            >
                              <title>
                                {`${row.month}: reported average ${row.avg_price} ${row.unit}; minimum ${row.min_price}; maximum ${row.max_price}; n=${row.sample_count}`}
                              </title>
                            </rect>
                          ))}
                          {records.map((row, index) => (
                            <g key={`${row.month}-${row.location}-${row.unit}`}>
                              <line
                                x1={x(index)}
                                x2={x(index)}
                                y1={y(row.max_price)}
                                y2={y(row.min_price)}
                                className="trend-range-line"
                              />
                              <line
                                x1={x(index) - 5}
                                x2={x(index) + 5}
                                y1={y(row.max_price)}
                                y2={y(row.max_price)}
                                className="trend-range-cap"
                              />
                              <line
                                x1={x(index) - 5}
                                x2={x(index) + 5}
                                y1={y(row.min_price)}
                                y2={y(row.min_price)}
                                className="trend-range-cap"
                              />
                              <title>
                                {`${row.month}: average ${row.avg_price}, minimum ${row.min_price}, maximum ${row.max_price}; source-reported samples: ${row.sample_count}`}
                              </title>
                              <text
                                x={x(index)}
                                y="246"
                                textAnchor="middle"
                                className="trend-month-label"
                              >
                                {new Date(`${row.month}T12:00:00`).toLocaleDateString(
                                  rw ? "rw-RW" : "en-US",
                                  { month: "short", year: "2-digit" }
                                )}
                              </text>
                              <text
                                x={x(index)}
                                y="266"
                                textAnchor="middle"
                                className="trend-sample-label"
                              >
                                n={row.sample_count}
                              </text>
                            </g>
                          ))}

                        </svg>
                      </div>
                      <p className="monthly-trend-summary">
                        {t(
                          `${records.length} monthly records shown. Values are source-provided and are not a forecast.`,
                          `Hagaragajwe imibare y'amezi ${records.length}. Iyi mibare yatanzwe n'inkomoko kandi si iteganyabiciro.`
                        )}
                      </p>
                    </>
                  );
                })()
              ) : (
                <div className="price-trends-empty">
                  {t(
                    "No monthly records match this product, unit, and location.",
                    "Nta mibare ya buri kwezi ijyanye n'igicuruzwa, igipimo n'ahantu wahisemo."
                  )}
                </div>
              )}
            </div>

            <div className="price-trends-meta">
              <span>
                {priceData
                  ? t(
                      `${priceData.total_matching_records.toLocaleString()} matching records`,
                      `Imibare ijyanye n'ibyo wahisemo: ${priceData.total_matching_records.toLocaleString()}`
                    )
                  : t("Preparing price data…", "Amakuru y'ibiciro arimo gutegurwa…")}
              </span>
              {priceData?.source && <span>{priceData.source}</span>}
            </div>

            {priceLoading && (
              <div className="price-trends-state" role="status">
                {t("Loading price summaries…", "Amakuru y'ibiciro arimo kuzanwa…")}
              </div>
            )}

            {priceError && (
              <div className="price-trends-state price-trends-error" role="alert">
                <p>
                  {t(
                    "Price summaries could not be loaded. Check that the backend is running and the dataset is available.",
                    "Amakuru y'ibiciro ntiyabashije kuboneka. Reba niba backend ikora kandi dataset iboneka."
                  )}
                </p>
                <button type="button" onClick={() => setPriceRefresh(current => current + 1)}>
                  {t("Retry", "Ongera ugerageze")}
                </button>
              </div>
            )}

            {!priceLoading && !priceError && priceData && (
              <>
                <div className="price-trends-table-wrap">
                  <table className="price-trends-table">
                    <thead>
                      <tr>
                        <th>{t("Month", "Ukwezi")}</th>
                        <th>{t("Product", "Igicuruzwa")}</th>
                        <th>{t("Region", "Intara")}</th>
                        <th>{t("Location", "Ahantu")}</th>
                        <th>{t("Unit", "Igipimo")}</th>
                        <th>{t("Minimum", "Igiciro cyo hasi")}</th>
                        <th>{t("Average", "Impuzandengo")}</th>
                        <th>{t("Maximum", "Igiciro cyo hejuru")}</th>
                        <th>{t("Samples", "Ibipimo")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {priceData.records.map((record, index) => (
                        <tr
                          key={`${record.month}-${record.product}-${record.unit}-${record.location}-${index}`}
                        >
                          <td>
                            {new Date(`${record.month}T12:00:00`).toLocaleDateString(
                              rw ? "rw-RW" : "en-US",
                              { month: "short", year: "numeric" }
                            )}
                          </td>
                          <td>{record.product}</td>
                          <td>{record.region}</td>
                          <td>{record.location}</td>
                          <td>{record.unit}</td>
                          <td className="price-trends-number">
                            {Number(record.min_price).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                          </td>
                          <td className="price-trends-number">
                            {Number(record.avg_price).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                          </td>
                          <td className="price-trends-number">
                            {Number(record.max_price).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                          </td>
                          <td>{record.sample_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {priceData.records.length === 0 && (
                    <div className="price-trends-empty">
                      {t(
                        "No records match these filters. Try another month or use Reset filters above.",
                        "Nta makuru ajyanye n'ibyo wahisemo abonetse. Gerageza ukundi kwezi cyangwa ukoreshe Siba amayungurura iri hejuru."
                      )}
                    </div>
                  )}
                </div>

                <div className="price-trends-pagination">
                  <span>
                    {priceData.total_matching_records === 0
                      ? t("No records", "Nta makuru")
                      : t(
                          `Showing ${priceOffset + 1}–${Math.min(priceOffset + priceData.records.length, priceData.total_matching_records)} of ${priceData.total_matching_records}`,
                          `Hagaragajwe ${priceOffset + 1}–${Math.min(priceOffset + priceData.records.length, priceData.total_matching_records)} kuri ${priceData.total_matching_records}`
                        )}
                  </span>
                  <div>
                    <button
                      type="button"
                      disabled={priceOffset === 0 || priceLoading}
                      onClick={() => setPriceOffset(offset => Math.max(0, offset - pricePageSize))}
                    >
                      {t("Previous", "Ibanjirije")}
                    </button>
                    <button
                      type="button"
                      disabled={
                        priceLoading ||
                        priceOffset + priceData.records.length >= priceData.total_matching_records
                      }
                      onClick={() => setPriceOffset(offset => offset + pricePageSize)}
                    >
                      {t("Next", "Ibikurikira")}
                    </button>
                  </div>
                </div>
              </>
            )}

            <p className="price-trends-footnote">
              {t(
                "Prices are displayed as supplied; no currency symbol is shown because the currency is unconfirmed. Different units must not be compared directly. Source file: data/raw/tangabid/tangabid_six_month_price_trends.csv",
                "Ibiciro bigaragazwa uko byatanzwe; nta kimenyetso cy'ifaranga cyakoreshejwe kuko ifaranga ritaramenyekana. Ibipimo bitandukanye ntibigomba kugereranywa mu buryo butaziguye. Dosiye y'inkomoko: data/raw/tangabid/tangabid_six_month_price_trends.csv"
              )}
            </p>
          </section>
        </main>
      )}

      {page === "about" && (
        <main className="inner-page about-page">
          <button className="back-link" onClick={() => navigate("home")}>← Garuka ku ntangiriro</button>
          <div className="inner-heading">
            <span className="section-kicker">{t("WHY MENYA NEZA AI", "IMPAMVU YA MENYA NEZA AI")}</span>
            <h1>From data to <em>{t("understanding.", "busobanuro.")}</em></h1>
            <p>{t("Our goal is to make useful information easier for communities and institutions to understand, question, and use responsibly.", "Intego yacu ni ugufasha abaturage n'inzego gusobanukirwa amakuru abafitiye akamaro, kuyasesengura no kuyakoresha neza.")}</p>
          </div>
          <div className="about-grid">
            <article className="about-card"><span>01</span><h3>{t("Start with data", "Tangira ku makuru")}</h3><p>{t("Use traceable sources, document the time period, and check data quality before drawing conclusions.", "Koresha amakuru afite inkomoko izwi, werekane igihe yakusanyirijwe kandi ugenzure ubwiza bwayo mbere yo gufata imyanzuro.")}</p></article>
            <article className="about-card"><span>02</span><h3>{t("Explain clearly", "Sobanura mu buryo bwumvikana")}</h3><p>{t("Help people understand what a finding means, what is uncertain, and what information is missing.", "Fasha abantu gusobanukirwa n'icyo ibyagaragajwe bisobanura, ibitaramenyekana neza n'amakuru abura.")}</p></article>
            <article className="about-card"><span>03</span><h3>{t("Prepare responsibly", "Tegura mu buryo bwitondewe")}</h3><p>{t("Support informed decisions without pretending historical data is a live forecast or official alert.", "Fasha abantu gufata ibyemezo bishingiye ku makuru, utagaragaza imibare yo mu bihe byashize nk'iteganyagihe cyangwa umuburo wemewe uriho ubu.")}</p></article>
          </div>
          <div className="about-notice"><b>{t("What the current version can do", "Ibyo iyi verisiyo ishobora gukora")}</b><p>{t("This prototype explores historical NISR Seasonal Agricultural Survey 2025 crop-production data and its quality checks. It does not yet provide validated disaster-risk predictions, live weather, or official warnings.", "Iyi verisiyo y'igerageza isesengura imibare y'umusaruro w'ibihingwa yo muri NISR Seasonal Agricultural Survey 2025 n'igenzura ry'ubwiza bwayo. Kugeza ubu ntirashobora gutanga ibyahanuwe byemejwe ku byago by'ibiza, amakuru y'ikirere y'ako kanya cyangwa imbuzi zemewe.")}</p></div>
          <button className="primary-button" onClick={() => navigate("area")}>{t("Explore the available data", "Reba amakuru ahari")} <span>↗</span></button>
        </main>
      )}

      <footer className="footer">
        <div className="footer-main">
          <div className="footer-intro">
            <button className="brand footer-brand" onClick={() => navigate("home")}>
              <span className="brand-mark">
                <img src="/menya-neza-ai-logo.png" alt="" />
              </span>
              <span className="brand-copy">
                <strong>MENYA NEZA <i>AI</i></strong>
                <small>{t("FROM DATA TO EARLY ACTION", "DUHERA KU MIBARE TUGAFASHA ABANTU KWITEGURA")}</small>
              </span>
            </button>
            <p>{t(
              "Understand the data. Prepare for change.",
              "Sobanukirwa n'amakuru. Witegure impinduka."
            )}</p>
            <small>{t(
              "Built with respect for data quality and local knowledge.",
              "Twubakiye ku bwiza bw'amakuru no ku bumenyi bw'abaturage."
            )}</small>
          </div>

          <div className="footer-link-group">
            <h3>{t("Explore", "Genzura")}</h3>
            <button onClick={() => navigate("home")}>{t("Home", "Ahabanza")}</button>
            <button onClick={() => navigate("area")}>{t("Check My Area", "Menya Akarere")}</button>
          </div>

          <div className="footer-link-group">
            <h3>{t("Analysis", "Ubusesenguzi")}</h3>
            <button onClick={() => navigate("insights")}>{t("Insights", "Ibyo imibare itugaragariza")}</button>
            <button onClick={() => navigate("origins")}>{t("Supply Origins", "Aho umusaruro ukomoka")}</button>
            <button onClick={() => navigate("seasonal")}>{t("Seasonal Comparison", "Kugereranya ibihembwe")}</button>
            <button onClick={() => navigate("intelligence")}>{t("Market Intelligence", "Ubusesenguzi bw'amasoko")}</button>
            <button onClick={() => navigate("quality")}>{t("Data Quality & Sources", "Ubwiza n'inkomoko by'amakuru")}</button>
          </div>

          <div className="footer-link-group">
            <h3>{t("About", "Umushinga")}</h3>
            <button onClick={() => navigate("about")}>{t("About MENYA NEZA AI", "Ibyerekeye MENYA NEZA AI")}</button>
            <button onClick={() => {
              setLanguage(rw ? "en" : "rw");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}>{rw ? "English" : "Kinyarwanda"}</button>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-meta">RWANDA <span>•</span> VERSION 0.2.0</div>
          <p className="footer-disclaimer">{t(
            "Historical survey statistics are not live forecasts or official warnings.",
            "Imibare y'ubushakashatsi bwo mu bihe byashize si iteganyagihe rigezweho cyangwa umuburo wemewe."
          )}</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
