
### `src/worker.js`

And this is the standalone code to put in GitHub:

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
