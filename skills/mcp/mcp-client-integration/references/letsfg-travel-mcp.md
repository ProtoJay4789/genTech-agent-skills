# LetsFG — worked example of an MCP client onboarding

The travel search-and-booking MCP that backs `travel.gentechlabs.net`. Kept as the concrete
reference for the generic procedure in `SKILL.md`; the shape repeats across vendors.

## Identity

| | |
|---|---|
| Project | `LetsFG/LetsFG` — MIT, agent-native flight & hotel search and booking |
| Site / human UI | `https://letsfg.co` |
| **MCP endpoint** | `https://letsfg.co/mcp` (Streamable HTTP) |
| OAuth metadata | `https://letsfg.co/developers/api/.well-known/oauth-authorization-server` |
| Register | `https://letsfg.co/developers/api/oauth/register` (RFC 7591, dynamic, **no allowlist**) |
| Authorize / consent | `https://letsfg.co/connect` (this *is* the authorization endpoint) |
| Token | `https://letsfg.co/developers/api/oauth/token` |
| Scopes | `flights:search` `flights:book` `hotels:search` `hotels:book` `profile:read` `openid` `email` |
| Grants | `authorization_code`, `refresh_token` |
| Auth methods | `client_secret_basic`, `none` |

Client registered for the fleet: `lfg_client_QnXG1QrXU7MhuVqmnro3XA`, redirect
`http://localhost:8899/callback`, `token_endpoint_auth_method: none`.
**PKCE S256 is mandatory** — an authorize request without a challenge is refused.

## Credential storage

- `profiles/gentech/secrets/letsfg-token.json` — mode 600. Holds `access_token` (1h),
  `refresh_token`, `scope`, `token_type: Bearer`.
- The **refresh token** is what gets bound into the consumer. `travel.gentechlabs.net` binds it as a
  Worker `secret_text` binding (`LETSFG_REFRESH_TOKEN`) plus `LETSFG_CLIENT_ID`, and refreshes on
  every call — no cron, no stale window.

## The tool groups (`tools/list` returns ~35)

- **Flights** — `search_flights`, `search_flights_flexible_dates`, `get_flight_results`,
  `present_flight_options`, `get_flight_details`, `get_flight_search_status`
- **Hotels** — `search_hotels`, `resolve_hotel_city`, `present_hotel_options`,
  `get_hotel_details`, `get_hotel_results`, `get_hotel_search_status`
- **Booking** — `book_flight`, `get_flight_booking`, `answer_booking_question`,
  `stop_flight_booking`, `book_hotel`, `get_hotel_booking`, `cancel_hotel_booking`,
  `booking_setup`, `book_from_link`
- **Watching** — `watch_price`, `check_price` — this is the "travel agent that watches" layer,
  and the reason this server fits `00-HQ/travel-intelligence-layer-*.md`
- **Discovery** — `find_deals`, `explore_destinations`, `present_destinations`, `find_airports`,
  `open_shared_trip`
- **Account** — `get_traveller_profile`, `edit_my_details`, `change_payment_method`,
  `add_preference`, `get_preferences`, `remove_preference`

## Calling conventions specific to this server

- **Search is asynchronous.** `search_flights` returns `{search_id, status:"running"}` — then call
  `get_flight_results` with that id. The payload contains narration plus an instruction block that
  says to print a `say_now` line to the traveller and call again with `wait_for_all=true`. Poll
  until that instruction disappears; the settled response carries the ranked offers and per-offer
  `letsfg.co/en?...&offer=wo_...` links.
- **Never hand-write a `letsfg.co` link.** A bare `letsfg.co` or `/en` is the home page, not a
  flight. Use the offer links the tool returns, verbatim.
- **Search args that matter** — `origin`, `destination` (IATA), `date_from` (required); plus
  `cabin_class`, `currency`, `adults`, `max_stops`, `departure_time_from/to`, `refundable_only`,
  `airline_only`, `response_mode` (`summary` saves tokens), `max_results`.
- The results text reports its own cross-check: it prices the same itineraries against Google
  Flights, Skyscanner and Kayak and keeps the cheapest seller. Useful as an independent confirmation
  when the user has a Google Flights screenshot.

## The wallet lane (no card, no account)

`POST https://letsfg.co/api/agent-access/request` → **402** with a `WWW-Authenticate: Payment`
header. The base64 `request` field decodes to:
`{amount: "10000", currency: "0x20c0…0000", methodDetails: {chainId: 4217}, recipient: "0xb1198f…"}`
— i.e. **$0.01 USDC on Tempo (chainId 4217)**, verification only, not a fee. Decode it before
promising the user this path; it is only cheaper than OAuth if a Tempo wallet is already funded.
OAuth is the free lane and needs one tap.

## Consumer surface

`travel.gentechlabs.net` — Worker `gentech-travel`. Paths: `/` (page), `/health`, `/api/trip`
(trip as data, from the `TRIP` binding), `/api/search?origin=&destination=&date=`, `/api/tools`.

**Superseded:** the older `gentech-travel-agent` Worker is orphaned (no route) and points at a
deleted Vercel deployment; its `/flights` still 500s. Do not resurrect it — `gentech-travel`
replaced it.
