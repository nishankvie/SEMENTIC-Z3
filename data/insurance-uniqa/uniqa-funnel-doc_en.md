# UNIQA Online Health Insurance Calculator — Journey Documentation

**Source**: [uniqa.at/rechner/krankenversicherung](https://www.uniqa.at/rechner/krankenversicherung/)
**Status**: Captured May 2026 (live behavior may change — teams should walk through to verify)
**Drop-off data**: Period Dec 10, 2025 – Feb 1, 2026 (source: UNIQA funnel analysis)

---

## 🎯 Scope Constraint — READ THIS FIRST

Before reading this journey doc: there is a **hard scope boundary** for this hackathon track. Not all paths in the calculator are in coaching scope.

| In Scope ✅ | Out of Scope ❌ |
|---|---|
| **Private doctor tariffs** ("Bei Arztbesuchen" — Start & Optimal) | **Hospital tariffs** ("Im Krankenhaus" — Sonderklasse path) |
| **"Myself only"** — insurance for yourself | **"Other persons"** — insurance for others (routes to advisor) |
| **Online-purchasable tariffs** (Start & Optimal) | **Advisor-required tariffs** (Opt. Plus & Premium — routes to appointment booking) |
| **All information currently collected in the calculator must still be collected** — no steps may be removed | Advisor handoff is a valid exit, but **not a conversion success** for this track |

**Conversion for this track = online purchase completion (Start or Optimal).** Anything that routes to an advisor is outside the coaching scope — it's a clean exit, not a conversion win.

The Conversion Coach **only coaches** users who can complete online (private doctor, "myself", Start/Optimal). Users on hospital paths, "other persons" paths, or Opt. Plus/Premium are cleanly routed to an advisor — no coaching.

**All information currently asked in the calculator must still be collected.** No steps may be removed from the in-scope path. The coach may not skip or remove anything — it may only intervene to support completion.

---

## Funnel Overview

The journey is structured in four visible phases (progress bar):
**Inputs → Product → Recommendation → Closing**

Funnel tracking identifies 15 steps, 4 of which are critical drop-off points. The most important branching happens early — whoever selects "in hospital" follows a different path than "at doctor visits."

The calculator's conversion logic ends in two ways:
1. **Online purchase** possible for the **Start** and **Optimal** tariffs (private doctor tariff "at doctor visits") — **this is the coaching scope**
2. **Advisor required** for **Opt. Plus**, **Premium**, and for all hospital tariffs and all constellations with "other persons" → the funnel ends in an appointment booking instead of an online purchase — **this is outside the coaching scope**

**For this hackathon track, only path 1 (online purchase) is in scope.** Path 2 routes to an advisor and is not further coached. This means:
- Hospital selection in Step 1 → immediately out of scope, coach routes to advisor
- "Other persons" in Step 2 → immediately out of scope, coach routes to advisor
- Opt. Plus/Premium in Step 4 → coach explains that these require a consultation, and either routes to advisor or supports selection of Start/Optimal

All information currently asked in the calculator remains in place. The coach does not simplify data collection — it supports users in navigation and completion.

---

## Key Steps in Detail

### Step 1 — Where do you want coverage?

**Phase**: Inputs
**Question**: "Where would you like to be covered?"
**UI**: Two large cards, multiple selection possible
**Options**:
- **At doctor visits** (public/private doctor, conventional & alternative medicine, telemedicine)
- **In hospital** (public hospital or private clinic, comfort in double room, flexible surgery scheduling)

**Branching**: The selection determines completely different follow-up paths. "Doctor visits" leads to the private doctor tariff logic (4 tariffs with online purchase option), "hospital" leads to the Sonderklasse path (more complex, almost always requires consultation).

**⚡ Scope note**: Only "At doctor visits" is in coaching scope. Anyone selecting "In hospital" (or both) is routed by the coach to an advisor — no further coaching. All data currently asked in the calculator remains in place.

**UX observation**: No explanation of what the consequence of the selection is. Users who want "everything" will likely click both — making the path even more complex. The coach should transparently communicate that the hospital path requires a consultation, while the doctor visit path can be completed online.

---

### Step 2 — For whom?

**Phase**: Inputs
**Question**: "Who should be insured?"
**Options**:
- **Myself** → Online purchase possible ✅ **In scope**
- **Other persons** → automatic advisor path ("Insurance for other persons is more complex") ❌ **Out of scope**

**Branching**: "Other persons" effectively ends the online path and routes directly to appointment booking.

**⚡ Scope note**: Only "Myself" is in coaching scope. The coach must recognize when someone selects "other persons" and cleanly route to an advisor. All information currently asked remains in place.

---

### Step 3 — Personal data for premium estimate

**Phase**: Inputs
**Question**: "To calculate a provisional individual premium for you, we need:"
**Required fields**:
- Date of birth
- Social insurance number

**Critical point**: This is where real personal data is requested for the first time, before any price has been shown. This is a classic trust barrier.

**⚡ Scope note**: This step remains unchanged. All data must still be collected. The coach can build trust here (e.g., explain why this data is needed), but cannot remove any steps.

---

### Step 4 — ⚠️ Tariff selection: First price display (66% drop-off)

**Phase**: Product
**Question**: "What coverage should your private doctor insurance include?"

**Info box** (above the tariffs):
> "Think about your current needs, not your needs in 20 years. After 3 years, you can switch to another of our four tariffs without a new health assessment!"

**UI**: Comparison table with 4 tariffs side by side:

| Tariff | Annual maximum | Provisional premium | Status |
|---|---|---|---|
| **Start** | €1,400 | **€38.74** | Available online ✅ |
| **Optimal** | €2,800 | **€68.14** | Available online ✅ |
| **Opt. Plus** | €4,200 | **€96.66** | Advisory only ❌ |
| **Premium** | €8,400 | **€140.16** | Advisory only ❌ |

Broken down by coverage areas: medical services, medications/vaccinations, therapeutic treatments, medical aids, refractive eye surgery.

**⚡ Scope note**: Only Start and Optimal are conversion targets (online-purchasable). Opt. Plus and Premium are visible in the calculator but route to an advisor. The coach should transparently explain to users clicking Opt. Plus/Premium that these require a consultation, and support them in selecting Start/Optimal — rather than encouraging them to stay on an advisory-required path.

**Why such high drop-off (66%)?** Several plausible reasons:
- First concrete number in the funnel — price shock
- Four options with five different price axes = cognitive overload
- The two more attractive tariffs (Opt. Plus, Premium) are only available after consultation → frustration for users who wanted to complete online
- ROPO effect: "Looked at the price online, will buy from an advisor later" — not trackable, but UNIQA reports it as real
- Information need regarding unfamiliar terms ("refractive eye surgery", "medical aids")

**Conversion Coach task**: This is the **most important intervention moment**. Possible hooks:
- Show market comparison ("Your tariff is cheaper than 80% of private doctor tariffs")
- Display term explanation boxes on hover/click
- Show tariff recommendation instead of full comparison matrix for uncertain users
- On Opt. Plus/Premium click: transparently explain that these require a consultation, and point to Start/Optimal as online-purchasable alternatives
- "What does it cost per day?" — psychological reframing (€38.74/month = €1.27/day)

---

### Step 5 — Add-on coverage selection (24% drop-off) — ❌ OUTSIDE COACHING SCOPE

**Phase**: Product (hospital path)
**Question**: "What insurance coverage are you interested in?"

**Options (select from existing)**:
- Sonderklasse after accident
- Sonderklasse Select Compact
- Sonderklasse Select Optimal
- Sonderklasse treatments after accident
- Sonderklasse treatments after accident and serious illnesses
- Sonderklasse treatments for all medically necessary treatments with deductible
- Hospital daily allowance
- Transport cost reimbursement
- Child accompaniment costs
- Medical second opinion
- Psychological counseling in emergency situations
- Lump sum for malignant neoplasms (cancer)
- Outpatient diagnostics
- Midwife (self-employed)

**Additional services**:
- VitalPlan prevention and fitness
- Daily allowance

**⚡ Scope note**: This step is **only relevant for the hospital path**, which is outside the coaching scope. Users who selected "At doctor visits" (private doctor) will not reach this step. Users who selected "In hospital" will be routed by the coach to an advisor — no further coaching on this path. The existence of this step in the calculator remains unchanged (all info is still collected), but the coach does not intervene here.

**UX observation**: For "hospital" selection, the user is confronted with ~15 possible modules, with footnotes and cross-references. Lower drop-off than Step 4 (24% vs 66%), but those who reach this point have already survived Step 4 and tend to be more determined.

---

### Step 6 — Health questions

**Phase**: Inputs (detailed data collection)
**Question**: (Details not fully captured — teams should verify this live)

**Known from briefing**: At this point, UNIQA collects health data needed to calculate the **final** premium (vs. the "provisional premium" from Step 4).

**⚡ Scope note**: This step remains unchanged. All health questions must still be answered. The coach can build trust and provide guidance here, but cannot remove or skip any questions.

---

### Step 7 — ⚠️ Final price after personal details (78% drop-off)

**Phase**: Recommendation
**Question**: Finalized premium after health assessment
**Consequence**: This is where the real, individualized price is shown. It can differ significantly from the provisional premium in Step 4.

**Why even higher drop-off (78%)?**
- Price has likely changed — usually upward (risk surcharge)
- If the final price is significantly higher than the initial estimate, the user feels misled
- Loss of trust: "why was something different shown before?"
- If there are deductible options, an additional decision must be made

**Conversion Coach task**: Damage control needed here. Possible hooks:
- Transparency about why the price changed
- Alternative tariff recommendation if the final price doesn't fit (focus on Start/Optimal — these are online-purchasable)
- "You can still complete online" — many users no longer realize this
- If user wants Opt. Plus/Premium: transparent note that a consultation is required, and offer Start/Optimal as online-purchasable alternatives

---

### Steps 8–11 — Advisor request path — ❌ OUTSIDE COACHING SCOPE

If the user is routed to the advisor path (hospital, other persons, Opt. Plus/Premium), several steps follow:

**Step "Where should the consultation take place?"**
- Online video consultation (NEW)
- In person at a UNIQA location
- By phone
- In person at home

**Step "Customer status"**
- New customer without advisor
- Existing customer, online consulting team
- Existing customer, personal advisor

**Step "Province"** (dropdown)

**Step "Service selection"** (which insurance line)
- Health Insurance, Pension/Life, Household, Accident, Car, Leasing, Legal Protection, Travel, Leisure, Insurance Policy Review

**Step "Date selection"** (calendar)

**Step "Appointment proposal"**

**Step "Personal data"** (name, email, phone, address, date of birth, occupation, social insurance, consultation topic)

**Step "Summary & confirmation"**

**⚡ Scope note**: The advisor request path is **outside the coaching scope**. The coach routes users here if they selected hospital, other persons, or Opt. Plus/Premium, and does not accompany them further. The steps remain unchanged in the calculator but are not actively supported by the coach.

**Observation**: The advisor path is also 7+ steps long and has several points where users might drop off — the funnel shifts the drop-off risk, it doesn't eliminate it. For the hackathon, this is not part of the measurement: conversion = online purchase.

---

### Step 12+ — Closing (Start / Optimal tariffs only) — ✅ IN SCOPE

**Phase**: Closing
The final steps for online purchase likely cover:
- Personal data (name, address, contact)
- Insurance start date / contract term
- Payment details
- Consents (terms & conditions, privacy policy)
- Purchase confirmation

**⚡ Scope note**: This is the target area of the Conversion Coach — users who reach this point should successfully complete the online purchase for Start or Optimal.

**These steps were not fully walked through during the journey documentation** (would require real personal data). Teams should verify this on the live calculator if needed.

---

## Observed Conversion Killers (Hypotheses for Teams)

The following hypotheses emerge from the journey structure and are intended as starting points for teams — not as established facts:

1. **Price shock at first price display** (Step 4 → 66% gone)
2. **Advisory requirement for the most attractive tariffs** creates frustration for online-affine users → coach should transparently communicate here and point to Start/Optimal as online-purchasable alternatives
3. **Gap between provisional and final premium** destroys trust
4. **Cognitive overload** from 4 tariffs × 6 coverage categories × footnotes
5. **Lack of explanation for technical terms** ("refractive eye surgery", "deductible", "Sonderklasse")
6. **No market comparison available** — users leave the page to compare and don't come back
7. **Social insurance number request** as a trust barrier
8. **"Advisory only" as a dead end** for users who explicitly wanted to complete online → coach should point to Start/Optimal as online-purchasable alternatives, rather than guiding users through the advisor labyrinth