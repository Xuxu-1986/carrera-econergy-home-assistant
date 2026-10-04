# Carrera Econergy for Home Assistant

Unofficial community integration for Carrera radiators controlled through the
Econergy cloud service.

> This project is not affiliated with, endorsed by, or supported by Carrera or
> Econergy. It relies on an undocumented cloud API and may stop working if that
> service changes.

## Current features

- Home Assistant UI configuration with Econergy email/password
- Automatic discovery of radiators and rooms
- Current and target temperature
- Modes: Manual, Program, Pilot wire and Frost protection
- Eco and Comfort temperatures
- Weekly program: 7 days × 3 time slots
- Open-window detection
- Daily/yesterday energy values
- Error/diagnostic sensor
- Automatic session re-authentication
- Cloud polling every 30 seconds

## Installation

### HACS custom repository

Until this repository is included in the default HACS catalog, add its GitHub
URL as a custom repository of type **Integration**, install **Carrera Econergy**,
then restart Home Assistant.

### Manual

Copy `custom_components/carrera_econergy` into your Home Assistant `/config/custom_components/`
directory and restart Home Assistant.

Then go to **Settings → Devices & services → Add integration → Carrera Econergy**
and enter the same credentials used by the Econergy application.

## Weekly programming

Each radiator exposes three program slots per day. Start/end times and slot
activation are available as Home Assistant entities. An advanced
`carrera_econergy.set_programs` service can replace all 21 slots at once.

## Energy sensor warning

The Econergy fields `powerConsoToday` and `powerConsoYesterday` are currently
interpreted as Wh and exposed as kWh. This unit interpretation has not yet been
independently documented by the manufacturer, so treat these values as
experimental.

## Privacy and security

Credentials are stored by Home Assistant in the integration config entry.
This repository contains no user email, password, session token, home ID or
radiator ID.

## Known limitations

- Cloud connection is required.
- The API is undocumented and unofficial.
- Only hardware/firmware observed during development has been tested so far.
- Program entities are intentionally low-level in v0.1.0.

## Contributing

Reports from owners of other Carrera/Econergy radiator models are especially
useful. When opening an issue, never publish your email, password, session
token, home ID or full API responses containing personal identifiers.
