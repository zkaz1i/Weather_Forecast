const form = document.querySelector(".city-form");
const body = document.body;
const todayRow = document.getElementById("hourly-today");
const nextRow = document.getElementById("hourly-next");
const tabButtons = document.querySelectorAll("[data-target]");
const extendedToggle = document.getElementById("extendedToggle");
const extendedPanel = document.getElementById("extendedPanel");
const weeklyAll = document.getElementById("weekly-all");
const weeklyNext = document.getElementById("weekly-next");
const weekTabButtons = document.querySelectorAll("[data-week-target]");
const timeNode = document.getElementById("currentTime");
const dateNode = document.getElementById("currentDate");
const weatherVideo = document.getElementById("weatherVideo");

const menuOpen = document.getElementById("menuOpen");
const drawerClose = document.getElementById("drawerClose");
const sideDrawer = document.getElementById("sideDrawer");
const drawerOverlay = document.getElementById("drawerOverlay");
const useMyLocationBtn = document.getElementById("useMyLocationBtn");
const addFavoriteBtn = document.getElementById("addFavoriteBtn");
const favBtnLabel = document.getElementById("favBtnLabel");
const saveDefaultCityBtn = document.getElementById("saveDefaultCityBtn");
const defaultCityInput = document.getElementById("defaultCityInput");
const tempUnitSeg = document.getElementById("tempUnitSeg");
const clockSeg = document.getElementById("clockSeg");
const prefNote = document.getElementById("prefNote");
const favoritesList = document.getElementById("favoritesList");
const favoritesEmpty = document.getElementById("favoritesEmpty");

function isUse24h() {
    return body && body.dataset.use24h === "true";
}

function openDrawer() {
    if (sideDrawer) sideDrawer.classList.add("open");
    if (drawerOverlay) drawerOverlay.classList.add("open");
}

function closeDrawer() {
    if (sideDrawer) sideDrawer.classList.remove("open");
    if (drawerOverlay) drawerOverlay.classList.remove("open");
}

if (menuOpen) {
    menuOpen.addEventListener("click", openDrawer);
}
if (drawerClose) {
    drawerClose.addEventListener("click", closeDrawer);
}
if (drawerOverlay) {
    drawerOverlay.addEventListener("click", closeDrawer);
}

if (useMyLocationBtn) {
    useMyLocationBtn.addEventListener("click", () => {
        if (!navigator.geolocation) {
            alert("Your browser does not support geolocation.");
            return;
        }
        useMyLocationBtn.disabled = true;
        useMyLocationBtn.textContent = "Locating…";
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const { latitude, longitude } = pos.coords;
                window.location.href = `/?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`;
            },
            () => {
                useMyLocationBtn.disabled = false;
                useMyLocationBtn.innerHTML = '<i class="fa-solid fa-map-pin"></i> Weather here';
                alert("Could not read your location. Check permissions and try again.");
            },
            { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
        );
    });
}

async function postJson(url, payload) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.error || "Request failed");
    }
    return data;
}

function setFavoriteButtonState(saved) {
    if (!addFavoriteBtn) return;
    const icon = addFavoriteBtn.querySelector("i");
    if (icon) {
        icon.classList.toggle("fa-solid", saved);
        icon.classList.toggle("fa-regular", !saved);
    }
    if (favBtnLabel) {
        favBtnLabel.textContent = saved ? "Saved" : "Add to favourites";
    }
}

function renderFavoritesList(cities) {
    if (!favoritesList) return;
    favoritesList.innerHTML = "";
    cities.forEach((city) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = `/?city=${encodeURIComponent(city)}`;
        a.textContent = city;
        const rm = document.createElement("button");
        rm.type = "button";
        rm.className = "fav-remove";
        rm.dataset.city = city;
        rm.setAttribute("aria-label", `Remove ${city}`);
        rm.innerHTML = '<i class="fa-solid fa-trash"></i>';
        li.appendChild(a);
        li.appendChild(rm);
        favoritesList.appendChild(li);
    });
    if (favoritesEmpty) {
        favoritesEmpty.classList.toggle("hidden", cities.length > 0);
    }
    favoritesList.classList.toggle("hidden", cities.length === 0);
}

if (addFavoriteBtn) {
    addFavoriteBtn.addEventListener("click", async () => {
        const city = addFavoriteBtn.dataset.city;
        if (!city) return;
        const saved = body.dataset.isFavorite === "true";
        addFavoriteBtn.disabled = true;
        try {
            if (saved) {
                const res = await fetch(`/api/favorites/${encodeURIComponent(city)}`, {
                    method: "DELETE",
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(data.error || "Could not remove favourite.");
                }
                body.dataset.isFavorite = "false";
                setFavoriteButtonState(false);
                if (data.favorites) {
                    renderFavoritesList(data.favorites);
                }
            } else {
                const data = await postJson("/api/favorites", { city });
                body.dataset.isFavorite = "true";
                setFavoriteButtonState(true);
                if (data.favorites) {
                    renderFavoritesList(data.favorites);
                }
            }
        } catch (e) {
            alert(e.message || "Could not update favourites.");
        } finally {
            addFavoriteBtn.disabled = false;
        }
    });
}

if (favoritesList) {
    favoritesList.addEventListener("click", async (e) => {
        const btn = e.target.closest(".fav-remove");
        if (!btn || !favoritesList.contains(btn)) {
            return;
        }
        const city = btn.dataset.city;
        if (!city) return;
        try {
            const res = await fetch(`/api/favorites/${encodeURIComponent(city)}`, {
                method: "DELETE",
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data.error || "Could not remove");
            }
            if (data.favorites) {
                renderFavoritesList(data.favorites);
            }
            const cur = (body.dataset.favoriteCity || "").toLowerCase();
            if (cur && cur === city.toLowerCase()) {
                body.dataset.isFavorite = "false";
                setFavoriteButtonState(false);
            }
        } catch (_) {
            window.location.reload();
        }
    });
}

async function savePrefs(partial) {
    if (prefNote) {
        prefNote.textContent = "";
    }
    try {
        await postJson("/api/preferences", partial);
        window.location.reload();
    } catch (e) {
        if (prefNote) {
            prefNote.textContent = e.message || "Could not save preferences.";
        }
    }
}

if (tempUnitSeg) {
    tempUnitSeg.querySelectorAll(".seg-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const useC = btn.dataset.celsius === "true";
            tempUnitSeg.querySelectorAll(".seg-btn").forEach((b) => {
                b.classList.toggle("active", b === btn);
            });
            savePrefs({ use_celsius: useC });
        });
    });
}

if (clockSeg) {
    clockSeg.querySelectorAll(".seg-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const use24 = btn.getAttribute("data-hour24") === "true";
            clockSeg.querySelectorAll(".seg-btn").forEach((b) => {
                b.classList.toggle("active", b === btn);
            });
            savePrefs({ use_24h_clock: use24 });
        });
    });
}

if (saveDefaultCityBtn && defaultCityInput) {
    saveDefaultCityBtn.addEventListener("click", async () => {
        try {
            await postJson("/api/preferences", { default_city: defaultCityInput.value });
            window.location.reload();
        } catch (e) {
            alert(e.message || "Could not save default city.");
        }
    });
}

function getWeatherVideoSet() {
    return {
        "weather-clear": {
            day: ["/static/videos/clear_day_fixed.mp4"],
            night: ["/static/videos/clear_night_fixed.mp4"],
        },
        "weather-sunny": {
            day: ["/static/videos/sunny_day_fixed.mp4"],
            night: ["/static/videos/clear_night_fixed.mp4"],
        },
        "weather-clouds": {
            day: ["/static/videos/clouds_day_fixed.mp4"],
            night: ["/static/videos/clouds_night_fixed.mp4"],
        },
        "weather-rain": {
            day: ["/static/videos/rain_day_fixed.mp4"],
            night: ["/static/videos/rain_night_fixed.mp4"],
        },
        "weather-drizzle": {
            day: ["/static/videos/drizzle_day_fixed.mp4"],
            night: ["/static/videos/drizzle_night_fixed.mp4"],
        },
        "weather-thunderstorm": {
            day: ["/static/videos/thunderstorm_day_fixed.mp4"],
            night: ["/static/videos/thunderstorm_night_fixed.mp4"],
        },
        "weather-snow": {
            day: ["/static/videos/snow_day_fixed.mp4"],
            night: ["/static/videos/snow_night_fixed.mp4"],
        },
        "weather-mist": {
            day: ["/static/videos/mist_day_fixed.mp4"],
            night: ["/static/videos/mist_night_fixed.mp4"],
        },
    };
}

function applyWeatherVideo(weatherClass, timeClass) {
    const v = document.getElementById("weatherVideo");

    if (!v) return;

    const src = "/static/videos/clouds_day_fixed.mp4";

    v.pause();
    v.removeAttribute("src");
    v.load();

    setTimeout(() => {
        v.src = src;
        v.load();
        v.play().catch(err => console.log("Video error:", err));
    }, 100);
}

if (form) {
    form.addEventListener("submit", () => {
        const button = form.querySelector("button");
        if (button) {
            button.textContent = "Loading...";
            button.disabled = true;
        }
    });
}

if (body) {
    const weatherText = (body.dataset.weather || "").toLowerCase();
    let weatherClass = "weather-clear";
    const hour = new Date().getHours();
    const timeClass = hour >= 6 && hour < 18 ? "daytime" : "nighttime";

    if (weatherText.includes("thunder")) {
        weatherClass = "weather-thunderstorm";
    } else if (weatherText.includes("drizzle")) {
        weatherClass = "weather-drizzle";
    } else if (weatherText.includes("rain")) {
        weatherClass = "weather-rain";
    } else if (weatherText.includes("snow")) {
        weatherClass = "weather-snow";
    } else if (weatherText.includes("cloud")) {
        weatherClass = "weather-clouds";
    } else if (
        weatherText.includes("mist") ||
        weatherText.includes("haze") ||
        weatherText.includes("fog")
    ) {
        weatherClass = "weather-mist";
    } else if (weatherText.includes("sun")) {
        weatherClass = "weather-sunny";
    }

    body.classList.add(weatherClass);
    body.classList.add(timeClass);

    applyWeatherVideo(weatherClass, timeClass);
}

function updateDateTime() {
    const now = new Date();
    if (timeNode) {
        if (isUse24h()) {
            const h = String(now.getHours()).padStart(2, "0");
            const m = String(now.getMinutes()).padStart(2, "0");
            timeNode.textContent = `${h}:${m}`;
        } else {
            timeNode.textContent = now.toLocaleTimeString([], {
                hour: "numeric",
                minute: "2-digit",
            });
        }
    }
    if (dateNode) {
        const dd = String(now.getDate()).padStart(2, "0");
        const mm = String(now.getMonth() + 1).padStart(2, "0");
        const yyyy = now.getFullYear();
        dateNode.textContent = `${dd}/${mm}/${yyyy}`;
    }
}

updateDateTime();
setInterval(updateDateTime, 1000);

function buildNextDayRow() {
    if (!todayRow || !nextRow || nextRow.children.length > 0) {
        return;
    }

    const cards = Array.from(todayRow.querySelectorAll(".mini-card")).slice(0, 8);
    cards.forEach((card, index) => {
        const clone = card.cloneNode(true);
        const timeNode = clone.querySelector("p");
        const tempNode = clone.querySelector("p:last-child");
        if (timeNode && !clone.classList.contains("sunset")) {
            timeNode.textContent = `+1D ${timeNode.textContent}`;
        }
        if (tempNode && !clone.classList.contains("sunset")) {
            const raw = tempNode.textContent || "";
            const m = raw.match(/^(-?\d+)/);
            if (m) {
                const suffix = raw.slice(m[0].length);
                const baseTemp = parseInt(m[0], 10);
                if (!Number.isNaN(baseTemp)) {
                    const adjusted = baseTemp + (index % 2 === 0 ? 1 : 0);
                    tempNode.textContent = `${adjusted}${suffix}`;
                }
            }
        }
        nextRow.appendChild(clone);
    });
}

if (tabButtons.length && todayRow && nextRow) {
    buildNextDayRow();
    tabButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.target;
            tabButtons.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            if (target === "next") {
                todayRow.classList.remove("active");
                nextRow.classList.add("active");
            } else {
                nextRow.classList.remove("active");
                todayRow.classList.add("active");
            }
        });
    });
}

if (extendedToggle && extendedPanel) {
    extendedToggle.addEventListener("click", () => {
        const isVisible = extendedPanel.classList.toggle("show");
        extendedToggle.textContent = isVisible ? "Hide extended forecast" : "Extended forecast";
    });
}

function buildNextWeekRow() {
    if (!weeklyAll || !weeklyNext || weeklyNext.children.length > 0) {
        return;
    }
    const cards = Array.from(weeklyAll.querySelectorAll(".week-card"));
    cards.slice(1).forEach((card) => weeklyNext.appendChild(card.cloneNode(true)));
}

if (weekTabButtons.length && weeklyAll && weeklyNext) {
    buildNextWeekRow();
    weekTabButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.weekTarget;
            weekTabButtons.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            if (target === "nextdays") {
                weeklyAll.classList.remove("active");
                weeklyNext.classList.add("active");
            } else {
                weeklyNext.classList.remove("active");
                weeklyAll.classList.add("active");
            }
        });
    });
}
