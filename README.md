# VoIP.ms Balance for Groundwire with Cloudflare Workers and Pushover

This project connects a VoIP.ms account to Groundwire using a Cloudflare Worker.

It provides two functions:

1. Groundwire can display the current VoIP.ms account balance.
2. Cloudflare can send the current balance to Pushover once a week.

No VPS or traditional server is required.

---

# Table of Contents

- [1. Overview](#1-overview)
- [2. Data Flow](#2-data-flow)
- [3. Requirements](#3-requirements)
- [4. Configure VoIP.ms API](#4-configure-voipms-api)
- [5. Understand the VoIP.ms API Response](#5-understand-the-voipms-api-response)
- [6. Create the Cloudflare Worker](#6-create-the-cloudflare-worker)
- [7. Add the Worker Code](#7-add-the-worker-code)
- [8. Configure Cloudflare Secrets](#8-configure-cloudflare-secrets)
- [9. Deploy and Test the Worker](#9-deploy-and-test-the-worker)
- [10. Configure Pushover](#10-configure-pushover)
- [11. Configure Groundwire](#11-configure-groundwire)
- [12. Configure Weekly Pushover Notifications](#12-configure-weekly-pushover-notifications)
- [13. Test the Complete Setup](#13-test-the-complete-setup)
- [14. Troubleshooting](#14-troubleshooting)
- [15. Security](#15-security)
- [16. Project Structure](#16-project-structure)
- [17. References](#17-references)
- [18. Final Setup Checklist](#18-final-setup-checklist)

---

# 1. Overview

The goal of this project is to make the VoIP.ms account balance available directly inside Groundwire and also receive a weekly balance notification through Pushover.

VoIP.ms provides the account balance through its API, but the response format is not the format expected by Groundwire's Custom Balance Checker.

The Cloudflare Worker acts as a small API adapter between the two systems.

The Worker:

1. Calls the VoIP.ms API.
2. Retrieves `balance.current_balance`.
3. Converts the value into a `balanceString`.
4. Returns the value to Groundwire.
5. On a weekly schedule, sends the balance to Pushover.

---

# 2. Data Flow

## 2.1 Groundwire balance lookup

When Groundwire checks the balance, the request flow is:

```text
┌──────────────┐
│  Groundwire  │
│   iPhone     │
└──────┬───────┘
       │
       │ GET /balance
       ▼
┌─────────────────────────┐
│   Cloudflare Worker     │
│                         │
│ /balance                │
└───────────┬─────────────┘
            │
            │ API request
            ▼
┌─────────────────────────┐
│       VoIP.ms API       │
│                         │
│       getBalance        │
└───────────┬─────────────┘
            │
            │ current_balance
            ▼
┌─────────────────────────┐
│ Cloudflare Worker       │
│                         │
│ {"balanceString":       │
│   "CAD $112.19"}        │
└───────────┬─────────────┘
            │
            ▼
┌──────────────┐
│  Groundwire  │
│              │
│ CAD $112.19  │
└──────────────┘
```

## 2.2 Weekly Pushover notification

The weekly notification follows a separate flow:

```text
┌──────────────────────┐
│ Cloudflare Cron      │
│ Trigger              │
│                      │
│ Every Sunday         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Cloudflare Worker    │
│                      │
│ scheduled()          │
└──────────┬───────────┘
           │
           │ getBalance()
           ▼
┌──────────────────────┐
│      VoIP.ms API     │
│                      │
│      getBalance      │
└──────────┬───────────┘
           │
           │ current_balance
           ▼
┌──────────────────────┐
│ Cloudflare Worker    │
│                      │
│ CAD $112.19          │
└──────────┬───────────┘
           │
           │ POST
           ▼
┌──────────────────────┐
│      Pushover        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│       iPhone         │
│                      │
│ VoIP.ms Balance      │
│ Current balance:     │
│ CAD $112.19          │
└──────────────────────┘
```

The Groundwire lookup and Pushover notification are independent.

A Groundwire balance request does not trigger a Pushover notification.

---

# 3. Requirements

Before starting, you need:

- A VoIP.ms account
- VoIP.ms API access
- A Cloudflare account
- A Cloudflare Worker
- Groundwire on iPhone/iPad
- A Pushover account if weekly notifications are wanted

You do not need:

- A VPS
- A traditional web server
- A database
- A computer running continuously
- A public IP address for your own server

---

# 4. Configure VoIP.ms API

## 4.1 Sign in to VoIP.ms

Go to:

https://voip.ms/

Sign in to your VoIP.ms account.

## 4.2 Open the API settings

In the VoIP.ms customer portal, go to:

**Main Menu → SOAP & REST/JSON API**

VoIP.ms API documentation:

https://wiki.voip.ms/article/API_Overview

## 4.3 Create an API password

Create/configure a dedicated API password.

This password is separate from the normal VoIP.ms portal password.

The API password will later be stored in Cloudflare as:

```text
VOIPMS_PASSWORD
```

Do not put the password into the Worker source code.

## 4.4 Enable API access

Enable API access on the VoIP.ms API configuration page.

VoIP.ms API access is disabled by default and must be enabled.

## 4.5 Configure the API IP whitelist

VoIP.ms requires API requests to originate from an allowed/whitelisted IP address.

The architecture is:

```text
Groundwire
    │
    │ HTTPS
    ▼
Cloudflare Worker
    │
    │ HTTPS API request
    ▼
VoIP.ms API
```

The request to VoIP.ms therefore comes from the Cloudflare Worker, not directly from Groundwire.

Configure the VoIP.ms API IP whitelist according to the current VoIP.ms API requirements.

VoIP.ms also provides a `getIP` API method that can be used to determine the IP address seen by the API.

Do not assume that the IP address of your iPhone is the address that needs to be whitelisted.

---

# 5. Understand the VoIP.ms API Response

The Worker uses the VoIP.ms REST API endpoint:

```text
https://voip.ms/api/v1/rest.php
```

The important API parameters are:

```text
api_username
api_password
method=getBalance
content_type=json
```

The API response contains the balance inside:

```text
balance.current_balance
```

For example:

```json
{
  "status": "success",
  "balance": {
    "current_balance": 112.192790,
    "spent_total": 21.05321
  }
}
```

The value we need is:

```text
112.192790
```

which comes from:

```text
balance.current_balance
```

## 5.1 Why the Cloudflare Worker is needed

Groundwire expects a response containing a `balanceString`.

For example:

```json
{
  "balanceString": "CAD $112.19"
}
```

VoIP.ms instead returns:

```json
{
  "status": "success",
  "balance": {
    "current_balance": 112.192790
  }
}
```

Therefore the Worker transforms:

```text
VoIP.ms response
       ↓
balance.current_balance
       ↓
112.192790
       ↓
CAD $112.19
       ↓
balanceString
```

Acrobits Groundwire Balance Checker documentation:

https://doc.acrobits.net/api/client/balance_checker/

---

# 6. Create the Cloudflare Worker

Go to:

https://dash.cloudflare.com/

Sign in.

Go to:

**Workers & Pages → Create application**

Select:

**Start with Hello World!**

Create the Worker.

For example:

```text
voipms-groundwire
```

Cloudflare will provide a URL similar to:

```text
https://voipms-groundwire.<your-subdomain>.workers.dev
```

Cloudflare Worker documentation:

https://developers.cloudflare.com/workers/get-started/dashboard/

---

# 7. Add the Worker Code

Open the Worker and choose:

**Edit code**

Replace the default code with:

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/balance") {
      const balance = await getBalance(env);

      if (balance === null) {
        return new Response("VoIP.ms API error", {
          status: 502
        });
      }

      return Response.json({
        balanceString: `CAD $${balance.toFixed(2)}`
      });
    }

    return new Response("Not found", {
      status: 404
    });
  },

  async scheduled(controller, env, ctx) {
    const balance = await getBalance(env);

    if (balance === null) {
      throw new Error("VoIP.ms API error");
    }

    const balanceString = `CAD $${balance.toFixed(2)}`;

    const response = await fetch(
      "https://api.pushover.net/1/messages.json",
      {
        method: "POST",
        body: new URLSearchParams({
          token: env.PUSHOVER_TOKEN,
          user: env.PUSHOVER_USER,
          title: "VoIP.ms Balance",
          message: `Current balance: ${balanceString}`
        })
      }
    );

    if (!response.ok) {
      throw new Error("Pushover API error");
    }
  }
};


async function getBalance(env) {
  const api = new URL(
    "https://voip.ms/api/v1/rest.php"
  );

  api.searchParams.set(
    "api_username",
    env.VOIPMS_USERNAME
  );

  api.searchParams.set(
    "api_password",
    env.VOIPMS_PASSWORD
  );

  api.searchParams.set(
    "method",
    "getBalance"
  );

  api.searchParams.set(
    "content_type",
    "json"
  );

  const response = await fetch(api);
  const data = await response.json();

  if (data.status !== "success") {
    return null;
  }

  return Number(
    data.balance.current_balance
  );
}
```

Click:

**Deploy**

---

# 8. Configure Cloudflare Secrets

The Worker needs four secret values.

Do not put these values directly into `worker.js`.

Go to:

**Workers & Pages → voipms-groundwire → Settings → Variables and Secrets**

Select:

**Add → Secret**

Cloudflare Secrets documentation:

https://developers.cloudflare.com/workers/configuration/secrets/

## 8.1 VOIPMS_USERNAME

Name:

```text
VOIPMS_USERNAME
```

Value:

```text
Your VoIP.ms login email
```

## 8.2 VOIPMS_PASSWORD

Name:

```text
VOIPMS_PASSWORD
```

Value:

```text
Your VoIP.ms API password
```

## 8.3 PUSHOVER_TOKEN

Name:

```text
PUSHOVER_TOKEN
```

Value:

```text
Your Pushover application token
```

## 8.4 PUSHOVER_USER

Name:

```text
PUSHOVER_USER
```

Value:

```text
Your Pushover user key
```

All four should be stored as:

**Secret**

After adding the secrets, deploy the Worker again.

---

# 9. Deploy and Test the Worker

Once the Worker and secrets are configured, test the `/balance` endpoint.

Open:

```text
https://voipms-groundwire.<your-subdomain>.workers.dev/balance
```

A successful response should look like:

```json
{
  "balanceString": "CAD $112.19"
}
```

The actual amount will depend on the VoIP.ms account.

If this works, the following path has been verified:

```text
Cloudflare Worker
       ↓
VoIP.ms API
       ↓
getBalance
       ↓
balance.current_balance
       ↓
balanceString
```

Do not configure Groundwire until this endpoint works.

---

# 10. Configure Pushover

Pushover is optional.

It is only required if you want the weekly balance notification.

Go to:

https://pushover.net/

Sign in or create an account.

Create a Pushover application.

Pushover will provide an application token.

Store that token in Cloudflare as:

```text
PUSHOVER_TOKEN
```

Your Pushover account also provides a user key.

Store that value as:

```text
PUSHOVER_USER
```

Pushover API documentation:

https://pushover.net/api

---

# 11. Configure Groundwire

Open Groundwire on the iPhone.

Go to the VoIP.ms account settings.

Open:

**Advanced Settings → Web Services → Custom Balance Checker**

Configure:

### URL

```text
https://voipms-groundwire.<your-subdomain>.workers.dev/balance
```

### Method

```text
GET
```

### POST Data

Leave empty.

### Username

Leave empty.

### Password

Leave empty.

### Custom Headers

Leave empty.

The Worker handles the VoIP.ms authentication.

The Groundwire request is therefore:

```text
Groundwire
    │
    │ GET /balance
    ▼
Cloudflare Worker
    │
    │ authenticated API request
    ▼
VoIP.ms
```

Groundwire Balance Checker documentation:

https://doc.acrobits.net/api/client/balance_checker/

---

# 12. Configure Weekly Pushover Notifications

The Worker already contains the:

```javascript
scheduled()
```

handler.

Cloudflare can execute this handler using a Cron Trigger.

Go to:

**Workers & Pages → voipms-groundwire → Settings → Triggers → Cron Triggers**

Click:

**Add Cron Trigger**

For a weekly Sunday notification at 14:00 UTC, use:

```text
0 14 * * SUN
```

This means:

```text
Every Sunday
14:00 UTC
```

Cloudflare Cron schedules use UTC.

For Toronto, this corresponds approximately to:

```text
10:00 AM during daylight time
9:00 AM during standard time
```

Cloudflare Cron documentation:

https://developers.cloudflare.com/workers/configuration/cron-triggers/

---

# 13. Test the Complete Setup

There are three separate things to test.

## 13.1 Test VoIP.ms → Cloudflare

Open:

```text
https://voipms-groundwire.<your-subdomain>.workers.dev/balance
```

Expected:

```json
{
  "balanceString": "CAD $112.19"
}
```

## 13.2 Test Cloudflare → Groundwire

Open Groundwire.

Open the keypad.

The balance should be displayed.

For example:

```text
CAD $112.19
```

## 13.3 Test Cloudflare → Pushover

For initial testing, temporarily configure a more frequent Cron Trigger.

For example:

```text
*/5 * * * *
```

This runs every five minutes.

Wait for the scheduled execution and verify that the Pushover notification arrives.

After testing, change the Cron Trigger back to the weekly schedule:

```text
0 14 * * SUN
```

Do not leave the five-minute schedule enabled unless that is intentional.

---

# 14. Troubleshooting

## Worker returns `Not found`

Make sure the URL contains:

```text
/balance
```

Correct:

```text
https://voipms-groundwire.<your-subdomain>.workers.dev/balance
```

Incorrect:

```text
https://voipms-groundwire.<your-subdomain>.workers.dev
```

## Worker returns `VoIP.ms API error`

Check:

- VoIP.ms API access is enabled.
- The VoIP.ms API username is correct.
- The VoIP.ms API password is correct.
- `VOIPMS_USERNAME` exists as a Cloudflare Secret.
- `VOIPMS_PASSWORD` exists as a Cloudflare Secret.
- The Worker was deployed after the secrets were created.
- The VoIP.ms API IP whitelist is correctly configured.

## Groundwire does not display the balance

First test the Worker directly:

```text
https://voipms-groundwire.<your-subdomain>.workers.dev/balance
```

It must return:

```json
{
  "balanceString": "CAD $112.19"
}
```

If the endpoint works, verify Groundwire:

```text
Settings
→ Accounts
→ VoIP.ms account
→ Advanced Settings
→ Web Services
→ Custom Balance Checker
```

Verify:

```text
Method: GET

URL:
https://voipms-groundwire.<your-subdomain>.workers.dev/balance
```

## Pushover notification does not arrive

Check:

```text
PUSHOVER_TOKEN
PUSHOVER_USER
```

Make sure both are configured as Cloudflare Secrets.

Verify that the token belongs to the correct Pushover application.

Verify the Pushover user key.

Check Cloudflare Worker logs and Cron event history.

## Cron does not appear to run

Go to:

```text
Workers & Pages
→ voipms-groundwire
→ Settings
→ Triggers
```

Verify the Cron Trigger.

For the weekly schedule:

```text
0 14 * * SUN
```

Remember that the schedule is UTC.

Cloudflare provides Cron event history in the Worker settings.

---

# 15. Security

Never commit the following values to GitHub:

```text
VOIPMS_PASSWORD
PUSHOVER_TOKEN
PUSHOVER_USER
```

Do not put credentials into:

- `worker.js`
- `README.md`
- URLs
- GitHub repositories
- screenshots
- public configuration files

Use Cloudflare Secrets instead.

If a credential is accidentally exposed, rotate it immediately.

The Worker only exposes the balance through `/balance`.

It does not expose the VoIP.ms credentials.

---

# 16. Project Structure

The recommended repository structure is:

```text
voipms-groundwire/
│
├── README.md
│
└── src/
    └── worker.js
```

`README.md` contains the complete setup and configuration instructions.

`src/worker.js` contains the Cloudflare Worker implementation.

---

# 17. References

## VoIP.ms

Website:

https://voip.ms/

API documentation:

https://wiki.voip.ms/article/API_Overview

REST API endpoint:

```text
https://voip.ms/api/v1/rest.php
```

API method:

```text
getBalance
```

Balance field:

```text
balance.current_balance
```

## Groundwire / Acrobits

Groundwire:

https://www.acrobits.net/groundwire/

Balance Checker API:

https://doc.acrobits.net/api/client/balance_checker/

Balance Checker setup:

https://faq.acrobits.net/set-up-your-balance-check-web-service

## Cloudflare

Cloudflare:

https://www.cloudflare.com/

Workers:

https://developers.cloudflare.com/workers/

Worker dashboard setup:

https://developers.cloudflare.com/workers/get-started/dashboard/

Secrets:

https://developers.cloudflare.com/workers/configuration/secrets/

Cron Triggers:

https://developers.cloudflare.com/workers/configuration/cron-triggers/

## Pushover

Pushover:

https://pushover.net/

Pushover API:

https://pushover.net/api

---

# 18. Final Setup Checklist

## VoIP.ms

- [ ] VoIP.ms account created
- [ ] API page opened
- [ ] API password configured
- [ ] API enabled
- [ ] API IP whitelist configured
- [ ] `getBalance` available

## Cloudflare

- [ ] Cloudflare account created
- [ ] Worker created
- [ ] Worker code deployed
- [ ] `VOIPMS_USERNAME` secret configured
- [ ] `VOIPMS_PASSWORD` secret configured
- [ ] `PUSHOVER_TOKEN` secret configured
- [ ] `PUSHOVER_USER` secret configured
- [ ] Worker deployed after secrets were added
- [ ] `/balance` tested successfully

## Groundwire

- [ ] Custom Balance Checker enabled
- [ ] Worker `/balance` URL configured
- [ ] Method set to `GET`
- [ ] Groundwire displays balance

## Pushover

- [ ] Pushover account created
- [ ] Pushover application created
- [ ] Application token configured
- [ ] User key configured
- [ ] Pushover notification tested

## Weekly notification

- [ ] Cloudflare Cron Trigger configured
- [ ] Weekly schedule configured
- [ ] Scheduled event verified
- [ ] Pushover notification received

---

# Final Architecture

After everything is configured, the final system looks like this:

```text
                         ┌──────────────────┐
                         │     VoIP.ms      │
                         │                  │
                         │   getBalance()   │
                         └────────┬─────────┘
                                  │
                                  │
                                  ▼
                     ┌────────────────────────┐
                     │    Cloudflare Worker   │
                     │                        │
                     │  VOIPMS_USERNAME       │
                     │  VOIPMS_PASSWORD       │
                     │                        │
                     │  /balance              │
                     │  scheduled()           │
                     └───────┬─────────┬──────┘
                             │         │
                    GET /balance       │ Cron
                             │         │
                             ▼         ▼
                    ┌─────────────┐  ┌───────────┐
                    │  Groundwire │  │ Pushover  │
                    │             │  │           │
                    │ CAD $112.19 │  │ Balance   │
                    └─────────────┘  └─────┬─────┘
                                           │
                                           ▼
                                        iPhone
```

The important separation is:

```text
Groundwire
   │
   └── /balance ──→ Cloudflare ──→ VoIP.ms


Cloudflare Cron
   │
   └── scheduled() ──→ VoIP.ms ──→ Pushover ──→ iPhone
```
