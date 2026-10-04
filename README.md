# VoIP.ms Groundwire Balance

A small Cloudflare Worker that integrates a VoIP.ms account with Acrobits Groundwire.

It provides:

- A `/balance` endpoint compatible with Groundwire's Custom Balance Checker.
- A weekly Pushover notification containing the current VoIP.ms balance.
- Secure storage of VoIP.ms and Pushover credentials using Cloudflare Secrets.

## How it works

```text
                         ┌──────────────────────┐
                         │      VoIP.ms API     │
                         │     getBalance()     │
                         └──────────┬───────────┘
                                    │
                                    │ current_balance
                                    ▼
                         ┌──────────────────────┐
                         │   Cloudflare Worker  │
                         │                      │
                         │ /balance             │
                         │ scheduled()          │
                         └───────┬────────┬──────┘
                                 │        │
                    Groundwire   │        │ Weekly
                                 │        │
                                 ▼        ▼
                         ┌────────────┐ ┌──────────┐
                         │ Groundwire │ │ Pushover │
                         │ CAD $xx.xx │ │  Alert   │
                         └────────────┘ └──────────┘
