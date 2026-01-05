# Teller Developer Documentation - Complete Reference

> This file contains the complete Teller API documentation concatenated for LLM context.

---

## Introduction

Source: https://teller.io/docs/index.md

---

# Welcome to the Teller Docs
## Explore our guides and documentation

Teller is a platform that provides instant access to bank account data and enables payments directly from bank accounts through a REST API.

**Getting Started:**

-   [Quickstart](/docs/guides/quickstart) - Learn key concepts and link your first financial account
-   [Teller Connect](/docs/guides/connect) - Integrate and customize Teller Connect for your application
-   [API Reference](/docs/api) - Complete API documentation

---

## Quickstart

Source: https://teller.io/docs/guides/quickstart.md

---

# Quickstart

Welcome to the Teller Quickstart. Here we will begin by introducing you to some key concepts and finish up by linking your first financial accounts to Teller.

## Introduction

This guide uses the `examples` repo from our [Github](https://github.com/tellerhq), which contains simple, pre-made applications for you to get up and running and experimenting with Teller as quickly as possible.

[tellerhq/examples](https://github.com/tellerhq/examples)

Grab your application id from the [Application Settings](https://teller.io/settings/application) page on the Dashboard. Your application id is how Teller Connect identifies which application it will be enrolling accounts for.

Next, you will need your Teller Client Certificate. A certificate and private key were created for you when you signed up for your Teller account. Check your downloads folder for `teller.zip`, which contains the certificate and private key created during sign-up. If you've misplaced your certificate or private key you can revoke your certificate and create a new one on the [Certificates](https://teller.io/settings/certificates) section of the Teller Dashboard.

> **Note**
>
> Just as your code uses our TLS certificate to verify it's really us on the end of the line, Teller uses client certificates so we can verify it's you that is making each API call.

## Setting up

Let's start by cloning the repo and running it on our local machine.

```bash
# Clone into the examples repo
git clone https://github.com/tellerhq/examples.git
cd examples

# Run the example application in sandbox mode
make APP_ID=YOUR_APP_ID

# Run in development mode to link real bank accounts
make APP_ID=YOUR_APP_ID ENV=development CERT=/path/to/cert.pem CERT_KEY=/path/to/private-key.pem
```

Congratulations, your app is now running in the `sandbox` environment! The `sandbox` is a free and unlimited test environment that enables you to simulate connections with various types of financial accounts without the need for real financial accounts. The `sandbox` does not connect to real financial institutions.

> **Note**
>
> You can make the application connect to real financial institutions by running it in the `development` environment.

## Linking your first financial account

All API requests interact with an `enrollment`, which is a Teller term equivalent to an end-user login at a financial institution. An end-user may have accounts at different financial institutions, which they can connect to your application by creating an `enrollment` for each institution. An `enrollment` is not the same as an individual financial institution account, although every financial institution account is associated with an `enrollment`, and it's common for an `enrollment` to have multiple financial accounts associated with it. For example, an end-user may have a checking account, a savings account, and a credit card all with the same financial institution; this would correspond to a single `enrollment` with three related financial accounts.

Open your browser and navigate to [localhost:8000](https://localhost:8000) and click the "Connect" button. You should now see Teller Connect, the UI we provide for end-users to safely and securely connect their financial accounts to your application.

Select a financial institution and use the following `sandbox` credentials to enroll:

```bash
User: username
Password: password
```

Finally, choose which accounts you want your application to be able to access.

Congratulations, you have successfully created your first enrollment! Now you can click the buttons that correspond to the various Teller API operations and see the data returned by the API.

Why not restart the application in `development` and try linking one of your own financial accounts?

---

## Teller Connect

Source: https://teller.io/docs/guides/connect.md

---

# Teller Connect

How to link your users' financial accounts to your application using Teller Connect

Interactive demo: [https://teller.io/connect/demo?appearance=system](https://teller.io/connect/demo?appearance=system)

## Introduction

Teller Connect is the client-side UI component that your users will use to connect their accounts to your application.

Teller Connect handles credential validation, multi-factor authentication, account selection, and error handling for every institution accessible using Teller.

## Flow Overview

Enrolling an end-user account using Teller Connect is very simple, and involves just three steps:

-   The end-user opens Teller Connect from within your application
-   The end-user selects their institution, authenticates with the financial institution and selects the accounts they want to share with your application
-   Teller Connect hands control back to your application with an access token you can use to access the end-user's accounts with the Teller API

## Integrating for the Web

Start by including the Teller Connect script in the HTML of your application.

```html
<script src="https://cdn.teller.io/connect/connect.js">
```

Including the script at the base of the body element is recommended so that it doesn't block rendering of your page, but it can run anywhere you choose to include it. The `async` attribute should be avoided for now as the inline code relies on the library being available, and the `defer` attribute should also not be used as we cannot rely on the DOMContentLoaded event firing after the library has been executed (currently some browsers will fire it before).

Next, setup Teller Connect by calling `TellerConnect.setup` with a valid configuration object. The bare minimum configuration is shown below, you can find a full list of supported properties later in this document.

```html
<html>
  <head></head>
  <body>
    <!-- When element is clicked, Teller Connect will open -->
    <button id="teller-connect">Connect to your bank</button>

    <!-- Body of your page... -->

    <!-- Part 1. Include the client library -->
    <script src="https://cdn.teller.io/connect/connect.js"></script>
    <script>
      // Part 2. Initialize & configure the client library
      document.addEventListener("DOMContentLoaded", function() {
        var tellerConnect = TellerConnect.setup({
          applicationId: "Your application ID e.g app_xxxxxx",
          // Teller's products that you would like to use, e.g. "verify"
          products: ["verify", ...],
          onInit: function() {
            console.log("Teller Connect has initialized");
          },
          // Part 3. Handle a successful enrollment's accessToken
          onSuccess: function(enrollment) {
            console.log("User enrolled successfully", enrollment.accessToken);
          },
          onExit: function() {
            console.log("User closed Teller Connect");
          }
        });

        // Part 4. Hook user actions to start Teller Connect
        var el = document.getElementById("teller-connect");
        el.addEventListener("click", function() {
          tellerConnect.open();
        });
      });
    </script>
  </body>
</html>
```

This code does three things:

-   Loads the Teller Connect loader in your page.
-   Initializes Teller Connect with a bare-bones configuration
-   Installs an event listener to present Teller Connect on a button click.

### Handling a Successful Enrollment

Once the user has enrolled Teller Connect will dismiss itself and return control to your application by invoking the `onSuccess` callback with a single parameter: the `enrollment` object.

```json
{
  "accessToken": "token_xxxxxxxxxxxxx",
  "user": {
    "id": "usr_xxxxxxxxxxxxx"
  },
  "enrollment": {
    "id": "enr_xxxxxxxxxxxxx",
    "institution": {
      "name": "Example Bank"
    }
  },
  "signatures": [
    "xxxxxxxxxxxxx"
  ]
}
```

The most important part of this payload is the `accessToken`, which you will use to access the end-user's accounts using the Teller API.

### Verifying Enrollment Object Signature

If a `nonce` was specified when initializing Teller Connect, the `enrollment` object will include a `signatures` element with a list of signatures that can be used to prevent token reuse attacks by verifying that the `accessToken` was generated by Teller during the current session.
The signatures are ED25519 with a SHA-256 digest and contain the following values concatenated with a dot: `nonce`, `accessToken`, `userId`, `enrollmentId`, and `environment`. Use the Token Signing Key from your application's Teller dashboard for verification.

> **Note**
>
>  The signatures element may contain multiple signatures to account for situations when we need to rotate our private keys. In such case you should be able to verify at least one of the signatures with the public key from your application's dashboard.

## Integrating for Other Platforms

Teller offers first-party support for other platforms including [Apple](https://github.com/tellerhq/tellerkit), [Android](https://github.com/tellerhq/connect-android) and [React](https://github.com/tellerhq/teller-connect-react). For instructions on how to integrate Teller Connect for those platforms, please consult each respective project's `README`.

## Repairing Disconnected Enrollments

Teller's connections are designed to be long-lasting. When a disconnection does occur, it's typically because something external changed—the user updated their banking password, the bank requires fresh MFA, or the institution needs the user to accept updated terms.

When an enrollment disconnects, Teller sends an [`enrollment.disconnected` webhook](/docs/api/webhooks) with a `reason` field indicating why. Common reasons include `disconnected.credentials_invalid` (password changed) and `disconnected.user_action.mfa_required` (bank requires fresh MFA).

To repair a disconnected enrollment, initialize Teller Connect with the `enrollmentId` of the disconnected enrollment:

```html
<script>
  var tellerConnect = TellerConnect.setup({
    applicationId: "app_xxxxxx",
    enrollmentId: "enr_xxxxxxxxxxxxx", // The disconnected enrollment's ID
    onSuccess: function(enrollment) {
      console.log("Enrollment repaired", enrollment.accessToken);
    },
    onExit: function() {
      console.log("User closed Teller Connect");
    }
  });

  tellerConnect.open();
</script>
```

When initialized with an `enrollmentId`, Teller Connect skips the institution picker and takes the user directly to the authentication flow for that enrollment's institution. After successful re-authentication, the existing enrollment is restored and the same `accessToken` continues to work.

## Configuration Options

The following properties are supported in the Teller Connect configuration object:

-   `applicationId` _(string, required)_ - A string representing your Application ID, which can be found inside the Teller Dashboard. Simply pass the value here, then we'll know who you are.

-   `environment` _(string, optional)_ - The environment to use for enrolling the user's accounts. Valid values are **"sandbox"**, **"development"** and **"production"**. The **"sandbox"** environment never communicates with a real institution, it is used to create sandbox enrollments, accounts and tokens. The **"development"** environment is the same as **"production"** but is not billed and has a hard limit of 100 enrollments.

-   `institution` _(string, optional)_ - When set to a valid institution id Teller Connect will skip its institution picker and load the first step for the corresponding institution. Use this to build your own picker experience.

-   `products` _(array, required)_ - List of Teller's products that you would like to use. The choice of
    products may determine which steps the user has to complete during
    enrollment. Valid values are:
    -   **"verify"** - account numbers and routing numbers (that are either available right after enrollment or require additional Teller Connect flows)
    -   **"verify.instant"** - account numbers and routing numbers that are available right after enrollment (see ['Verify Account Details via Microdeposit'](/docs/api/account/details#account-details-verification-via-microdeposit))
    -   **"balance"** - real-time account balances
    -   **"transactions"** - categorised transaction data
    -   **"identity"** - account-holder data
    -   **"payments"** (BETA) - send payments on behalf of your users

-   `selectAccount` _(string, optional)_ -
    -   **"disabled"** - automatically connect all the supported financial accounts associated with this user's account at the institution (default)
    -   **"single"** - the user will see a list of supported financial accounts and will select only one to share with your application
    -   **"multiple"** - the user will see a list of supported financial accounts and will select one or more to share with your application

-   `enrollmentId` _(string, optional)_ - An id of a previously created enrollment. Use to initialize Teller Connect in update mode to repair a disconnected enrollment.

-   `connectToken` _(string, optional)_ - A connect token is returned in a Teller API response when user interaction is required to complete the transaction, e.g. when multi-factor authentication is required to complete a payment. When initialized with a `connectToken` Teller Connect will guide the user through completing the transaction.

-   `nonce` _(string, optional)_ - Your application must choose an arbitrary string to allow for the cryptographic signing of the enrollment object passed to the `onSuccess` callback. This prevents token reuse attacks. The value must be randomly generated on the server and unique to the current session. If generated client-side, an attacker could reuse the nonce together with the enrollment object from another session to impersonate the victim.

-   `onSuccess` _(function, required)_ - Invoked with a single argument when the end-user has completed the flow. The argument is context dependent:

    -   An `enrollment` object upon successful enrollment
    -   A `payment` object when MFA was required to complete a payment
    -   A `payee` object when MFA was required to create a payee

    For more information about the format of `payment` and `payee` consult the Zelle guide.

-   `onInit` _(function, optional)_ - An optional callback that if supplied is invoked when Teller Connect finishes loading

-   `onExit` _(function, optional)_ - Fired when the end-user dismisses Teller Connect without enrolling an account.

-   `onFailure` _(function, optional)_ - An optional callback called when payee or payment creation fails. This function accepts one parameter: a `failure` object, which contains:

    -   `type` - the type of the failure. Possible values: payee, payment
    -   `code` - a machine readable failure code. Possible values: timeout, error
    -   `message` - a human readable failure message

    Example:

    ```json
    {
      "type": "payment",
      "code": "error",
      "message": "We were unable to complete the payment."
    }
    ```

---

## Environments

Source: https://teller.io/docs/guides/environments.md

---

# Environments

Teller provides three distinct environments for different stages of your integration: sandbox for UI testing, development for real-world testing, and production for live applications.

## Overview

Each environment serves a specific purpose in your integration journey. Choosing the right environment ensures you can test effectively while managing costs and access appropriately.

| Environment     | Data           | Cost | Enrollment Limit | Use Case                               |
| --------------- | -------------- | ---- | ---------------- | -------------------------------------- |
| **Sandbox**     | Simulated      | Free | Unlimited        | UI testing, flow development           |
| **Development** | Real bank data | Free | 100 enrollments  | Integration testing with real accounts |
| **Production**  | Real bank data | Paid | Unlimited        | Live applications                      |

## Sandbox

The sandbox environment uses simulated data and never connects to real financial institutions. It is ideal for:

-   Building and testing your UI integration
-   Simulating enrollment flows including MFA scenarios
-   Testing error handling without affecting real accounts

> **Note**
>
> Use `username` / `password` for successful enrollments, or `otp` / `password` to test MFA flows. See the [Sandbox guide](/docs/guides/sandbox) for all test credentials.

To use the sandbox environment, initialize [Teller Connect](/docs/guides/connect) with:

```javascript
TellerConnect.setup({
  applicationId: "app_xxxxxx",
  environment: "sandbox",
  // ...
});
```

## Development

The development environment connects to real financial institutions and returns real bank data. This is critical for validating your integration before going live.

> **Note**
>
> Development uses **real bank data**, not simulated data. When you or your testers connect accounts, you are accessing actual financial information.

### Key characteristics

-   **100 enrollment limit** — An enrollment represents one bank login, which may include multiple accounts (e.g., checking, savings, and credit card under the same login)
-   **Free to use** — No charges for the development environment
-   **Real institution connectivity** — Test against actual bank authentication flows, MFA requirements, and data formats
-   **Rate limits apply** — Same [rate limits](/docs/api#rate-limits) as production

### When to use development

Use the development environment when you need to:

-   Verify your application handles real transaction data correctly
-   Test against specific institutions your users will connect
-   Validate your webhook handlers with real enrollment events
-   Confirm your UI works with actual account structures

To use the development environment:

```javascript
TellerConnect.setup({
  applicationId: "app_xxxxxx",
  environment: "development",
  // ...
});
```

> **Note**
>
> API requests in development require your [client certificate](/docs/api/authentication), just like production.

## Production

The production environment is for live applications serving real end-users. Access to production requires completing Teller's Know Your Business (KYB) verification process.

### Requirements

To access production, you must complete KYB verification, which includes:

-   Company URL and product demonstration
-   Beneficial owner information
-   Business documentation

Contact Teller to begin the production access process.

### Transitioning to production

When moving from development to production:

1.  Update your Teller Connect configuration to use `environment: "production"`
2.  Ensure your webhook endpoints are production-ready
3.  Verify your certificate is valid and securely stored

```javascript
TellerConnect.setup({
  applicationId: "app_xxxxxx",
  environment: "production",
  // ...
});
```

## Choosing the right environment

**Start with sandbox** to build your UI and test enrollment flows without needing real credentials.

**Move to development** once your UI is working and you need to validate against real bank data. Use your own bank accounts or those of your team to test the full integration.

**Request production access** when you are ready to serve real end-users with a tested, working integration.

## Common questions

### Do enrollments in development count toward production?

No. Development and production are completely separate. Enrollments created in development do not transfer to production, and the 100-enrollment limit applies only to development.

### Can I reset my development enrollment count?

Deleting an enrollment does not restore your enrollment count. The limit represents total enrollments created, not active enrollments.

### What happens when I hit the development limit?

You will not be able to create new enrollments in development. Request production access when your integration is ready.

---

## Sandbox

Source: https://teller.io/docs/guides/sandbox.md

---

# Sandbox

The sandbox environment can be used to simulate and test a variety of scenarios you can encounter while using Teller without having to use real bank accounts.

> **Note**
>
> Use the sandbox environment by initializing Teller Connect with the `environment` property set to `sandbox`.

## Enrollments

Specific enrollment flows are triggered using a combination of the login credentials entered in Teller Connect after selecting an institution. In the sandbox environment, all institutions behave identically.

The valid login password is always `password` so if you want to simulate a bad credentials flow, all you need to do is provide a different value.

### Username Values

-   `username` _()_ - Leads to an immediate successful enrollment.

-   `otp` _()_ - Will follow an OTP MFA flow whereby the user will be asked to select a contact to send an OTP code. The correct code is `0000`

-   `challenge` _()_ - Triggers a knowledge-based MFA flow where the end-user is asked their favorite color. Your favorite color is `blue`.

-   `disconnected` _()_ - Results in a successful enrollment that will immediately disconnect upon the first request made to get data from it. Alternatively you can use any of the enrollment status reasons as usernames (e.g. `account_locked`).

-   `verify.microdeposit` _()_ - Used for testing the ['Verify Account Details via Microdeposit'](/docs/api/account/details#account-details-verification-via-microdeposit) flow.

## Payments

Sandbox payment flows are determined by the `memo` value that is used when issuing the create payment request. To get a payment that is immediately successful and does not require user intervention use any value (or none at all) that does not appear in the following list.

### Memo Values

-   `otp` _()_ - The create payment response will contain a `connect_token` that you can use to initialize Teller Connect and perform an OTP MFA flow whereby the user will be asked to select a contact to send an OTP code. The correct code is `0000`.

-   `otp_error` _()_ - This behaves similarly to the `otp` value but results in an error when the correct OTP code (`0000`) is used, simulating a failure from the financial institution. This failure can be observed with Teller Connect's `onFailure` hook.

---

## Introduction

Source: https://teller.io/docs/api.md

---

# Introduction

Welcome to the Teller API Reference

The Teller API is organized around REST. Resources have predictable, self-describing URLs and contain links to related resources. Our API accepts form-encoded requests and returns JSON encoded responses. It uses standard HTTP status codes, authentication, and methods in their usual ways.

You can use the Teller API in sandbox mode, which is free, does not call out to any real banks, and does not affect your live data. The access token you use determines whether your request is handled in the live or sandbox environments.

Access tokens for the live environment are obtained using Teller Connect when a user successfully connects a bank account to your Teller application.

> **Note**
>
> Learn how to integrate Teller Connect into your application with the [Teller Connect integration guide](/docs/guides/connect)

## Rate Limits

Teller enforces rate limits to maintain system stability and protect the integrity of connections with financial institutions. These limits help ensure that excessive traffic does not trigger hostile or defensive measures from banks, which could impact connectivity for all customers.

Free-tier accounts are subject to rate limits. The exact thresholds are not publicly documented and cannot be adjusted. If you’re on the free plan, design your integration to be efficient and resilient under these constraints.

Production plans benefit from significantly higher rate limits. In practice, it’s rare for production applications to hit these ceilings under normal usage. The limits are designed to balance performance with reliability—preventing overload scenarios that could degrade service quality for other customers.

Rate limiting is not just about controlling traffic. It is part of being a responsible participant in the broader financial ecosystem. By moderating the volume of requests sent to institutions, we help maintain long-term access, reduce the risk of disruption, and demonstrate respect for the operational boundaries of the banks we connect to. It reflects our commitment to being a good steward of shared infrastructure—for your users, for other developers, and for the institutions themselves.

If your application triggers rate limits, Teller will respond with an HTTP 429 status code. Your system should back off and retry after an appropriate delay.

## API Entrypoint

```bash
https://api.teller.io/
```

## Versioning

Teller uses dated versions with the latest one being 2020-10-12. By default all API requests will use the version specified in the [Teller Dashboard](https://teller.io/settings/application).

In order to test a new version, you can request it using the Teller-Version HTTP header. Once you are ready to upgrade to a new version permanently, you can do so from the dashboard. You will have 72 hours to rollback to the version you were previously using.

```bash
curl https://api.teller.io/accounts -H "Teller-Version: 2019-07-01"
```

---

## Authentication

Source: https://teller.io/docs/api/authentication.md

---

# Authentication

Nearly all of the Teller API endpoints require authentication. In this guide we'll look at mTLS and HTTP Basic Auth, which are the different types of authentication used in the Teller API and when and why they are used.

## mTLS

In a normal TLS handshake the client uses the server's TLS certificate to authenticate its identity. Because the server is in possession of a certificate signed by a trusted certificate authority, the client is able to verify all of the handshake messages were sent by the server and there was no third-party eavesdropping on or worse, tampering with the channel. Sadly this allows the server to verify neither the identity of the client nor that an attacker isn't snooping or tampering with the channel. Unfortunately it's not uncommon to misconfigure TLS certificate validation, thereby invalidating all of the aforementioned guarantees. Given that the Teller API facilitates access to some of the most sensitive and private information possible, a scenario where Teller is not able to verify the integrity and confidentiality of the API is not something we can allow to happen.

**The Teller API uses mTLS to authenticate the API caller**. Teller issues client certificates that you use to connect to the Teller API. This allows both parties to mutually authenticate each other, and most importantly enables Teller to authenticate API clients even when API clients are not performing TLS verification correctly.

mTLS is **required** for all API requests that involve end-user data, i.e. all requests in `development` and `production`.

In the interests of getting up and running as quickly as possible client authentication is not required in the `sandbox` environment, because it does not involve real end-user data. If used, client certificates are validated in the `sandbox` environment. We recommend using client certificates as soon as possible in order to become familiarized with them.

```bash
curl --cert /path/to/cert.pem --key /path/to/key.pem https://api.teller.io
```

Always keep your private key safe and secret. You must never share or distribute your private key, e.g. embedding it in a mobile app. If you suspect your private key has been compromised, you must revoke the certificate in the Teller Dashboard and issue a new one.

## Access Token

Access tokens are created when an end-user successfully completes an enrollment using Teller Connect. An access token represents your authorization to access accounts at a given financial institution that the end-user has expressly given consent for. Access tokens are useless without a Teller client certificate, in fact they are useless without a client certificate belonging to the application the user consented giving access to. The Teller API will not even acknowledge an access token is correct without the correct certificate.

Access tokens are encoded using the HTTP Basic Auth scheme.

```bash
curl -u ACCESS_TOKEN: https://api.teller.io/accounts
```

---

## Errors

Source: https://teller.io/docs/api/errors.md

---

# Errors

Learn how error conditions are expressed in the Teller API

Teller uses standard HTTP response status codes to indicate the success or failure of a request. Status codes in the 2xx range denote a successful request. Status codes in the 4xx range denote a client error, e.g. not using a client certificate to make the request, a problem with the user access token, etc. Status codes in the 5xx range denote a problem on our end, e.g. a bank is unavailable and it's not possible or otherwise doesn't make sense to gracefully handle the exception.

> **Note**
>
> Failed requests do not generate billing events

## Status Codes

Here is a list of status codes currently in use by the Teller API

-   `200 OK` _()_ - A successful request.

-   `400 Bad Request` _()_ - The request was unacceptable. Used when a request that requires a client certificate is made without one.

-   `401 Unauthorized` _()_ - A request was made without an access token where one was required.

-   `403 Forbidden` _()_ - A request was made with an invalid or revoked access token.

-   `404 Not Found` _()_ - The requested resource was not found.

-   `410 Gone` _()_ - Indicates that the resource requested is no longer available and that condition is permanent, e.g. because a financial account was closed.

-   `422 Unprocessable Entity` _()_ - A request was made with an invalid request body.

-   `429 Too Many Requests` _()_ - Indicates that the application has exceeded its rate limit by sending too many requests in a given time period and that this request was denied.

-   `502 Bad Gateway` _()_ - The financial institution is unavailable, or a 500 level response was received when making a request to the financial institution, and a graceful fallback is not possible, e.g. a payment instruction.

## The Error Object

Detailed information about the error condition is returned in the response body as a JSON object.

```json
{
  "error": {
      "code": "bad_request",
      "message": "Missing certificate: Retry request using your Teller client certificate."
  }
}
```

-   `error` _(object)_ - An object describing the error condition.
    -   `code` _(string)_ - The error condition.
    -   `message` _(string)_ - A human readable string describing the error and how to resolve it.

## Enrollment Errors

From time to time enrollments can enter an unhealthy state, meaning Teller is unable to use it until the end-user takes the required action. When your application makes a request involving a disconnected enrollment Teller returns a 404 status code with an error code beginning with `enrollment.disconnected`.

> **Note**
>
> To restore an unhealthy enrollment initialize Teller Connect in update mode and direct the user to reconnect.

When an enrollment enters a disconnected state, Teller can send a [webhook event](/docs/api/webhooks) of type `enrollment.disconnected`.

```json
{
  "error": {
    "code": "enrollment.disconnected.user_action.mfa_required",
    "message": "User MFA is required."
  }
}
```

## Enrollment Error Codes

-   `enrollment.disconnected` _()_ - A generic error used for when no more information is available.

-   `enrollment.disconnected.account_locked` _()_ - Access to the account has been restricted by the financial institution.

-   `enrollment.disconnected.credentials_invalid` _()_ - The end-user changed their authentication credentials to access the financial institution.

-   `enrollment.disconnected.enrollment_inactive` _()_ - The enrollment has become disconnected due to inactivity.

-   `enrollment.disconnected.user_action.captcha_required` _()_ - The end-user is required to solve a CAPTCHA.

-   `enrollment.disconnected.user_action.contact_information_required` _()_ - The end-user is required to update their contact information.

-   `enrollment.disconnected.user_action.insufficient_permissions` _()_ - The end-user does not have the required permissions to perform the requested operation.

-   `enrollment.disconnected.user_action.mfa_required` _()_ - The end-user is required to complete a MFA challenge.

-   `enrollment.disconnected.user_action.web_login_required` _()_ - The end-user is required to login to the financial institution's web online-banking, e.g. to accept FI terms and conditions.

---

## Webhooks

Source: https://teller.io/docs/api/webhooks.md

---

# Webhooks

Learn how to register your application to receive and verify webhook notifications from Teller and be notified of events not represented in the Teller API itself

## When Webhooks Are Triggered

Teller sends webhook events when specific conditions or changes are detected in user enrollments or their financial data. Webhooks are triggered in response to these events, which represent meaningful state changes within the Teller system.

For example, the `transactions.processed` webhook is sent when Teller finds new transactions after polling a user’s connected financial institution. Teller performs these checks multiple times per day on a non-predictable schedule, but guarantees at least one polling attempt every 24 hours.

Another example is the `enrollment.disconnected` webhook, which is triggered when Teller determines that an enrollment’s connection to the institution is irrecoverably broken and cannot be automatically restored.

These events can interact. For instance, if Teller temporarily loses connectivity to an enrollment but hasn’t yet classified it as disconnected, it may not be able to access up-to-date account data. As a result, no `transactions.processed` events will be sent during that time. Webhooks resume once connectivity is restored or the enrollment is marked as disconnected.

## Registering Webhooks

To register a new webhook, you need to have a URL in your app that Teller can call. You can configure a new webhook from the Teller Dashboard under [Application Settings](https://teller.io/settings/application).

Now, whenever something of interest happens in your app, a webhook is fired off by Teller. In the next section, we'll look at how to consume webhooks.

## Consuming Webhooks

When your app receives a webhook request from Teller, check the `type` attribute to see what event caused it. The first part of the event type categorizes the payload type, e.g., `enrollment`, `transaction`, etc.

```json
{
  "id": "wh_oiffb5cocakqmksbkg000",
  "payload": {
    "enrollment_id": "enr_oiffb5cocakqmksbkg001",
    "reason": "disconnected.account_locked"
  },
  "timestamp": "2023-07-10T03:49:29Z",
  "type": "enrollment.disconnected"
}
```

In the example above, an enrollment has entered a disconnected state because the financial institution has completely locked the account. This may happen for legal reasons, because an account has been involved in fraud, or an attacker has repeatedly tried to login by guessing the end user's credentials.

## The Webhook Object

The webhook object has the following shape:

-   `id` _(string)_ - The id of the webhook event

-   `payload` _(object)_ - Event specific data or an empty object if `"type": "webhook.test"`

-   `timestamp` _(string)_ - The ISO 8601 timestamp of the event.

-   `type` _(string)_ - The type of the event, either:
    -   `enrollment.disconnected` — Sent when the enrollment disconnected
    -   `transactions.processed` — Sent when transactions are categorized by Teller's transaction enrichment
    -   `account.number_verification.processed` - Sent when account details verification via microdeposit has either suceeded or expired (see ['Verify Account Details via Microdeposit'](/docs/api/account/details#account-details-verification-via-microdeposit))
    -   `webhook.test` — A test event triggered from the [Application Settings](https://teller.io/settings/application) page. Use this to test your webhook implementation.

The shape of the `payload` depends on the event's `type`

## Payload shape

-   `enrollment_id` _(string)_ - The id of the affected enrollment

-   `reason` _(string)_ -

    > Available when `"type": "enrollment.disconnected"` only

    The reason the enrollment was disconnected. Possible values:

    -   `disconnected`
    -   `disconnected.account_locked`
    -   `disconnected.credentials_invalid`
    -   `disconnected.enrollment_inactive`
    -   `disconnected.user_action.captcha_required`
    -   `disconnected.user_action.contact_information_required`
    -   `disconnected.user_action.insufficient_permissions`
    -   `disconnected.user_action.mfa_required`
    -   `disconnected.user_action.web_login_required`

-   `transactions` _(array)_ -

    > Available when `"type": "transactions.processed"` only

    An array of categorized transactions. The shape of the transaction objects is described in the [Transactions](/docs/api/account/transactions) page

-   `account_id` _(string)_ -

    > Available when `"type": "account.number_verification.processed"` only

    The id of the account the details of which needed to be verified

-   `status` _(string)_ -

    > Available when `"type": "account.number_verification.processed"` only

    The status of the verification. Possible values:

    -   `completed`
    -   `expired`

## Verifying Messages

Teller signs every webhook event with all non-expired signing secrets, that only you and Teller know. You can get your signing secrets from the [Application Settings](https://teller.io/settings/application) page.

Teller sends a signature in the Teller-Signature HTTP header:

```
Teller-Signature: t=signature_timestamp,v1=signature_1,v1=signature_2,v1=...
```

Most of the time there will be only one non-expired signing secret, so the signature header will look like this:

```
Teller-Signature: t=signature_timestamp,v1=signature
```

To verify that the payload was created by Teller, you have to calculate the signature and it must be equal to the signature extracted from the signature header.

To calculate the signature:

-   Create `signed_message` by joining `signature_timestamp` and the request's JSON body with a . character
-   Compute HMAC with SHA-256 using the non-expired signing secret as the key and `signed_message` as the message

To prevent replay attacks you should reject webhook events with a `signature_timestamp` (Unix time) older than 3 minutes.

## Expiring Secrets

When you have a policy to periodically roll secrets, Teller allows you to do it without a gap in signature verification.

To expire the current signing secret, go to the [Application Settings](https://teller.io/settings/application) page and select when the secret should expire, e.g. in 2 hours. When you press Save, Teller will create a new non-expired secret, and from that moment, Teller will sign all webhook events with both secrets until the old secret expires:

```
Teller-Signature: t=signature_timestamp,v1=signature_with_new_secret,v1=signature_with_old_secret
```

This gives you time to update your application with the new secret.

---

## Identity

Source: https://teller.io/docs/api/identity.md

---

# Identity

Identity provides you with all of the accounts the end-user granted your application access authorization along with beneficial owner identity information for each of them. Beneficial owner information is attached to each account as it's possible the end-user is not the beneficial owner, e.g. a corporate account, or there is more than one beneficial owner, e.g. a joint account the end-user shares with their partner.

## Properties

-   `type` _(string)_ - `person`, `organization` or `unknown`.

-   `names` _(array)_ - An array of `name` objects with the following shape: (can be an empty list)
    -   `type` _(string)_ - `name` or `alias`.
    -   `data` _(string)_ - Name of the person or organization.

-   `addresses` _(array)_ - An array of `address` objects. Can be an empty list.
    -   `primary` _(boolean)_ - Indicates if this is the owner's primary address (in case multiple addresses are provided).
    -   `data` _(object)_ -
        -   `street` _(string)_ - The street address.
        -   `city` _(string)_ - The name of the town or city.
        -   `region` _(string)_ - The state or region. For US addresses it's a 2-letter uppercase state code, e.g. "AL".
        -   `postal_code` _(string)_ - The zip or postal code. For US addresses it can be a 5-digit ZIP code or a ZIP+4 code: 5 and 4 digits separated with a hyphen.
        -   `country` _(string)_ - The ISO 3166-1 alpha-2 2-letter country codes, e.g. "US".

-   `phone_numbers` _(array)_ - An array of `phone_number` objects with the following shape: (can be an empty list)
    -   `type` _(string)_ - `mobile`, `home`, `work` or `unknown`.
    -   `data` _(string)_ - The phone number digits only or prefixed with a "+" if in an international (E.164) format.

-   `emails` _(array)_ - An array of `email` objects with the following shape: (can be an empty list)
    -   `data` _(string)_ - An email address.

***

## Get Identity

Returns an array of accounts with beneficial owner identity information attached. Each item in the list is an object of the following type:

### Properties

-   `account` _(object)_ - An `account` object. See the [documentation](/docs/api/accounts) for type information.

-   `owners` _(array)_ - An array of identity objects of the type defined [above](#properties).

```bash
curl https://api.teller.io/identity \
  -u test_token_ky6igyqi3qxa4:
```

```json
[
  {
      "account" : {
        "name" : "Essential Savings",
        "last_four" : "3528",
        "type" : "depository",
        "enrollment_id" : "enr_oiin624rqaojse22oe000",
        "id" : "acc_oiin624jqjrg2mp2ea000",
        "status" : "open",
        "links" : {
            "self" : "https://api.teller.io/accounts/acc_oiin624jqjrg2mp2ea000",
            "transactions" : "https://api.teller.io/accounts/acc_oiin624jqjrg2mp2ea000/transactions",
            "balances" : "https://api.teller.io/accounts/acc_oiin624jqjrg2mp2ea000/balances",
            "details" : "https://api.teller.io/accounts/acc_oiin624jqjrg2mp2ea000/details"
        },
        "institution" : {
            "id" : "security_cu",
            "name" : "Security Credit Union"
        },
        "subtype" : "savings",
        "currency" : "USD"
      },
      "owners" : [
        {
            "addresses" : [
              {
                  "primary" : true,
                  "data" : {
                    "postal_code" : "55305",
                    "street" : "4849 SYCAMORE FORK ROAD",
                    "region" : "MINNESOTA",
                    "country" : "US",
                    "city" : "HOPKINS"
                  }
              }
            ],
            "type" : "organization",
            "names" : [
              {
                  "data" : "URBAN GROCERIES INC",
                  "type" : "name"
              }
            ],
            "phone_numbers" : [
              {
                  "data" : "6667778888",
                  "type" : "mobile"
              }
            ],
            "emails" : [
              {
                  "data" : "urban_groceries_inc@example.com"
              }
            ]
        }
      ]
  },
...
]
```

---

## Accounts

Source: https://teller.io/docs/api/accounts.md

---

# Accounts

An Account represents an end-user's individual financial account at a given financial institution.

## Properties

-   `currency` _(string)_ - The ISO 4217 currency code of the account.

-   `enrollment_id` _(string)_ - The id of the enrollment that the account belongs to.

-   `id` _(object)_ - The id of the account itself.

-   `institution` _(object)_ - An object containing information about the financial institution that holds the account.
    -   `id` _(string)_ - The internal Teller id assigned to the financial institution.
    -   `name` _(string)_ - The name of the financial institution that holds the account.

-   `last_four` _(string)_ - The last four digits of the account number.

-   `links` _(object)_ - An object containing links to related resources. A link indicates the enrollment supports that type of resource. Not every institution implements all of the capabilities that Teller supports. Your application should reflect on the contents of this object to determine what is supported by the financial institution.
    -   `self` _(string)_ - A self link to the account.
    -   `details` _(string)_ - A link to the account's details, such as account number and routing numbers.
    -   `balances` _(string)_ - A link to the account's live balances.
    -   `transactions` _(string)_ - A link to the account's transactions.

-   `name` _(string)_ - The account's name.

-   `type` _(string)_ - The type of account. Either `depository` or `credit`.

-   `subtype` _(string)_ - The account's subtype.

    depository:
    checking, savings, money_market, certificate_of_deposit, treasury, sweep
    credit:
    credit_card

-   `status` _(string)_ - The account's status: `open` or `closed`. When \`closed it means that it's closed from Teller's perspective, i.e. Teller can still access live enrollment data from the institution, but the account itself is closed, Teller can no longer see that account, or the account transitioned to an insufficient-access state.

    When you try to request an account or any of its sub-resources, and that account is `closed`, Teller returns a 410 response with `account.closed` error. You should parse the error as a dot-separated string where the first token is account.closed and the subsequent tokens, if present, include the reason for closing.

***

## List Accounts

Returns a list of all accounts the end-user granted access to during enrollment in Teller Connect.

```bash
curl https://api.teller.io/accounts \
  -u test_token_ky6igyqi3qxa4:
```

```json
[
  {
      "enrollment_id" : "enr_oiin624rqaojse22oe000",
      "links" : {
        "balances" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/balances",
        "self" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000",
        "transactions" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/transactions"
      },
      "institution" : {
        "name" : "Security Credit Union",
        "id" : "security_cu"
      },
      "type" : "credit",
      "name" : "Platinum Card",
      "subtype" : "credit_card",
      "currency" : "USD",
      "id" : "acc_oiin624kqjrg2mp2ea000",
      "last_four" : "7857",
      "status" : "open"
  },
  ...
]
```

***

## Get Account

Retrieve a specific account by it's id.

```bash
curl https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000 \
  -u test_token_ky6igyqi3qxa4:
```

```json
{
    "enrollment_id" : "enr_oiin624rqaojse22oe000",
    "links" : {
      "balances" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/balances",
      "self" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000",
      "transactions" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/transactions"
    },
    "institution" : {
      "name" : "Security Credit Union",
      "id" : "security_cu"
    },
    "type" : "credit",
    "name" : "Platinum Card",
    "subtype" : "credit_card",
    "currency" : "USD",
    "id" : "acc_oiin624kqjrg2mp2ea000",
    "last_four" : "7857",
    "status" : "open"
}
```

***

## Delete Account

This deletes your application's authorization to access the given account as addressed by its id. This does not delete the account itself.

Removing access will cancel billing for subscription billed products associated with the account, e.g. transactions.

```bash
curl -X DELETE https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000 \
  -u test_token_ky6igyqi3qxa4:
```

```json
// No response body, e.g. 204 No Content
```

***

## Delete Accounts

This deletes your application's authorization to access any account in the
enrollment, i.e. effectively deletes the enrollment. This does not delete
the accounts themselves.

Removing access will cancel billing for subscription billed products
associated with the enrollment, e.g. transactions.

```bash
curl -X DELETE https://api.teller.io/accounts \
  -u test_token_ky6igyqi3qxa4:
```

```json
// No response body, e.g. 204 No Content
```

---

## Account Details

Source: https://teller.io/docs/api/account/details.md

---

# Account Details

The account details object contains the financial account's account number and routing information.

## Properties

-   `account_id` _(string)_ - The id of the account the account details belong to.

-   `account_number` _(string)_ - The account number.

-   `links` _(object)_ - An object containing links to related resources. A link indicates the enrollment supports that type of resource. Not every institution implements all of the capabilities that Teller supports. Your application should reflect on the contents of this object to determine what is supported by the financial institution.
    -   `self` _(string)_ - A self link to the account details.
    -   `account` _(string)_ - A link to the account that owns the details.

-   `routing_numbers` _(object)_ - An object containing the account details routing numbers.
    -   `ach` _(string (nullable))_ - The account's routing number for ACH transactions.
    -   `wire` _(string (nullable))_ - The account's wire routing number.
    -   `bacs` _(string (nullable))_ - The account's BACS sort code.

***

## Get Account Details

Returns the account's details.

```bash
curl https://api.teller.io/accounts/acc_oiin624iajrg2mp2ea000/details \
  -u test_token_ky6igyqi3qxa4:
```

```json
{
  "links" : {
      "account" : "https://api.teller.io/accounts/acc_oiin624iajrg2mp2ea000",
      "self" : "https://api.teller.io/accounts/acc_oiin624iajrg2mp2ea000/details"
  },
  "routing_numbers" : {
      "ach" : "066474405"
  },
  "account_id" : "acc_oiin624iajrg2mp2ea000",
  "account_number" : "142999287346"
}
```

***

## Account Details verification via Microdeposit

Account details are available instantly after an enrollment for the majority of
institutions supported by Teller. These institutions have the `verify.instant`
product in the response from the [Institutions API
endpoint](/docs/api/institutions). However, this is not possible for a number of
institutions (those that have `verify.microdeposit` products in the API response
from the [Institutions API endpoint](/docs/api/institutions)). To access
account details from these institutions, you can implement the 'Verify Account
Details via Microdeposit\` flow. Your customers will enter account and routing
numbers for the accounts that they would like to enroll in Teller Connect, and
Teller will send a microdeposit to the accounts to verify that they are
correct.

### Enabling / disabling the flow

To enable the flow, [initialize Teller
Connect](/docs/guides/connect#configuration-options) with `verify` specified among
the products using the `products` property. To disable the flow and only
enable institutions that provide account details instantly, specify
the `verify.instant` product instead.

If you don't need account details but would like to enroll users with the
institutions that require this flow to use other Teller products, don't
specify `verify` product when initializing Teller Connect. Your users won't be
prompted to enter account numbers when they enroll.

### Accessing Account Details

When using this flow, account details become available after a successful
verification: once we've confirmed that the microdeposit sent by us is present
among the account's transactions, we'll make the account details available via
the API. This usually happens within 3 business days. You can also subscribe to
an `account.number_verification.processed` [webhook](/docs/api/webhooks) to be
notified about completed verifications.

While the verification is pending, the `/accounts/:account_id/details` API
endpoint will return a `404 Not Found` error with the following body:

```json
{
  "error": {
    "code": "account_number_verification_pending",
    "message": "Account details are not yet available because the verification via microdeposit is pending"
  }
}
```

If we are not able to verify the details entered by the user within 7 calendar
days, the verification expires, and the `/accounts/:account_id/details` API
endpoint will start returning a `404 Not Found` error with the following body:

```json
{
  "error": {
    "code": "account_number_verification_expired",
    "message": "Account details are not available because the verification via microdeposit has expired"
  }
}
```

We'll also send a `account.number_verification.processed` webhook when the
verification expires.

### Testing the flow in Sandbox

To test this flow in [Sandbox](/docs/guides/sandbox), [initialize Teller
Connect](/docs/guides/connect#configuration-options) with `verify` product and use
`verify.microdeposit` as the username in Teller Connect. You'll get access to
two accounts called `Success` and `Failure`, and you'll be asked to enter the
account number and routing number for both. Enter any number that ends with the
account number suffix shown in Teller Connect and any valid routing number
(e.g. `110000000`).

After enrolling you can fetch account details to see what the response
looks like when the verification is pending. Verification is triggered by
fetching transactions: if you make an API call to fetch transactions for the
account called `Success`, a microdeposit transaction will be present in the
response and the account details verification will succeeed. You'll then be
able to fetch account details from the API.

If you make an API call to fetch transactions for the account called `Failure`,
there won't be a microdeposit transaciton present and the verification will
expire. If you make an API call to fetch account details, you'll get an error
saying that the verification has expired.

### Considerations

Consider using [`selectAccount` configuration
parameter](/docs/guides/connect#configuration-options) in Teller Connect to limit the
number of accounts your users enroll or let the user select which accounts they
want to enroll to avoid making users enter details for the accounts that you
don't need access to.

When a verification expires, the enrollment remains healthy and you might be
billed for it, so consider [disconnecting such
enrollments](/docs/api/accounts#delete-accounts) if you don't need access to the
enrollment.

---

## Account Balances

Source: https://teller.io/docs/api/account/balances.md

---

# Account Balances

The account balances API provides your application with live, real-time account
balances. At least one balance (ledger or available) is always provided.

## Properties

-   `account_id` _(string)_ - The id of the account the account balances belong to.

-   `ledger` _(string (nullable))_ - The account's ledger balance. The ledger balance is the total amount of funds in the account.

-   `available` _(string (nullable))_ - The account's available balance. The available balance is the ledger balance net any pending inflows or outflows.

-   `links` _(object)_ - An object containing links to related resources. A link indicates the enrollment supports that type of resource. Not every institution implements all of the capabilities that Teller supports. Your application should reflect on the contents of this object to determine what is supported by the financial institution.
    -   `self` _(string)_ - A self link to the account balances.
    -   `account` _(string)_ - A link to the account that owns the balances.

***

## Get Account Balances

Returns the account's balances.

```bash
curl https://api.teller.io/accounts/acc_oiin624iajrg2mp2ea000/balances \
  -u test_token_ky6igyqi3qxa4:
```

```json
{
  "ledger" : "28575.02",
  "links" : {
      "account" : "https://api.teller.io/accounts/acc_oiin624iajrg2mp2ea000",
      "self" : "https://api.teller.io/accounts/acc_oiin624iajrg2mp2ea000/balances"
  },
  "account_id" : "acc_oiin624iajrg2mp2ea000",
  "available" : "28575.02"
}
```

---

## Transactions

Source: https://teller.io/docs/api/account/transactions.md

---

# Transactions

The transactions API exposes the ledger transactions of a financial account.

> **Note**
>
> The initial call to the transactions API can sometimes time out with accounts that have an abnormally large number of transactions. Should this happen wait a few seconds and try again.

## Properties

-   `account_id` _(string)_ - The id of the account that the transaction belongs to.

-   `amount` _(string)_ - The signed amount of the transaction as a string.

-   `date` _(string)_ - The ISO 8601 date of the transaction.

-   `description` _(string)_ - The unprocessed transaction description as it appears on the bank statement.

-   `details` _(object)_ - An object containing additional information regarding the transaction added by Teller's transaction enrichment.
    -   `processing_status` _(string)_ - Indicates the transaction enrichment processing status. Either `pending` or `complete`.
    -   `category` _(string (nullable))_ - The category that the transaction belongs to. Teller uses the following values for categorization: `accommodation`, `advertising`, `bar`, `charity`, `clothing`, `dining`, `education`, `electronics`, `entertainment`, `fuel`, `general`, `groceries`, `health`, `home`, `income`, `insurance`, `investment`, `loan`, `office`, `phone`, `service`, `shopping`, `software`, `sport`, `tax`, `transport`, `transportation`, and `utilities`.
    -   `counterparty` _(object)_ - An object containing information regarding the transaction's recipient
        -   `name` _(string (nullable))_ - The processed counterparty name.
        -   `type` _(string (nullable))_ - The counterparty type: `organization` or `person`.

-   `status` _(string)_ - The transaction's status: `posted` or `pending`.

-   `id` _(string)_ - The id of the transaction itself.

-   `links` _(object)_ - An object containing links to related resources. A link indicates the enrollment supports that type of resource. Not every institution implements all of the capabilities that Teller supports. Your application should reflect on the contents of this object to determine what is supported by the financial institution.
    -   `self` _(string)_ - A self link to the transaction.
    -   `account` _(string)_ - A link to the account that the transaction belongs to.

-   `running_balance` _(string (nullable))_ - The running balance of the account that the transaction belongs to. Running balance is only present on transactions with a `posted` status.

-   `type` _(string)_ - The type code transaction, e.g. `card_payment`.

***

## List Transactions

Returns a list of all transactions belonging to the account.

### Pagination

The Transactions endpoint returns all transactions for the given account. Usually this does not represent a large amount of data transfer, but if your application has specific requirements of minimizing the amount of data going over the wire the transactions list endpoint supports pagination controls.

Pagination controls are given as query params on the request URL.

-   `count` _(integer)_ - The maximum number of transactions to return in the API response.

-   `from_id` _(string)_ - Paginate backward from this transaction. Returns transactions older than the one with this ID. For recent activity, use date ranges or webhooks.

-   `start_date` _(string)_ - Filter transactions to include only those on or after this date (inclusive). Must be in ISO 8601 format, for example 2025-01-01.

-   `end_date` _(string)_ - Filter transactions to include only those on or before this date (inclusive). Must be in ISO 8601 format, for example 2025-01-31.

```bash
curl https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/transactions \
  -u test_token_ky6igyqi3qxa4:
```

```json
[
  {
    "details" : {
      "processing_status" : "complete",
      "category" : "general",
      "counterparty" : {
          "name" : "YOURSELF",
          "type" : "person"
      }
    },
    "running_balance" : null,
    "description" : "Transfer to Checking",
    "id" : "txn_oiluj93igokseo0i3a000",
    "date" : "2023-07-15",
    "account_id" : "acc_oiin624kqjrg2mp2ea000",
    "links" : {
      "account" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000",
      "self" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/transactions/txn_oiluj93igokseo0i3a000"
    },
    "amount" : "86.46",
    "type" : "transfer",
    "status" : "pending"
  },
  ...
]
```

***

## Get Transaction

Returns an individual transaction.

```bash
curl https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/transactions/txn_oiluj93igokseo0i3a005 \
  -u test_token_ky6igyqi3qxa4:
```

```json
{
  "running_balance" : null,
  "details" : {
     "category" : "service",
     "counterparty" : {
        "type" : "organization",
        "name" : "CARDTRONICS"
     },
     "processing_status" : "complete"
  },
  "description" : "ATM Withdrawal",
  "account_id" : "acc_oiin624kqjrg2mp2ea000",
  "date" : "2023-07-13",
  "id" : "txn_oiluj93igokseo0i3a005",
  "links" : {
     "account" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000",
     "self" : "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/transactions/txn_oiluj93igokseo0i3a005"
  },
  "amount" : "42.47",
  "type" : "atm",
  "status" : "posted"
},
```

***

## Syncing Transactions

Use these patterns to fetch only new transactions without re-downloading your full history.

### Using date ranges

Use `start_date` and `end_date` to bound your sync window; both dates are inclusive. Expand the window 7-10 days beyond your last sync to capture transactions that shift dates when moving from `pending` to `posted`.

When a pending transaction posts, its date often changes to the posting date. If you only query from your last sync date forward, you may miss these transactions.

```bash
curl -G "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/transactions" \
  -d "start_date=2025-01-01" \
  -d "end_date=2025-01-31" \
  -u test_token_ky6igyqi3qxa4:
```

Your expanded window will return transactions you've already stored. Reconcile by matching on transaction ID: insert new records and update existing ones. If the date range returns more than `count` transactions, use `from_id` to paginate through the rest of the window.

> **Note**
>
> Teller maintains stable transaction IDs. Occasionally, when a pending transaction changes significantly upon posting and cannot be matched to the original, it's created as a new record with a new ID. Account for this in your reconciliation.

### Using webhooks

Subscribe to [`transactions.processed`](/docs/api/webhooks) to receive notifications when new transactions are available. Teller refreshes your enrollments at least once per day. When new transactions are found, this webhook fires, and you call the transactions API to retrieve them.

---

## Payments

Source: https://teller.io/docs/api/account/payments.md

---

# Payments

> **Note**
>
> This is a beta API and as such the interface is subject to change

The payments resource allows you to send payments to yourself or a 3rd party on behalf of the end-user from their account. Currently the only supported payment scheme is Zelle, but others will be added in the future.

## Zelle

Zelle payments can be initiated from checking accounts. The funds are debited immediately from the payer account and are usually received by the beneficiary instantly. In cases where the receiving financial institution is not a member of the Zelle network, the funds will settle via ACH with the beneficiary receiving the funds around 3 days after.

***

## Create a Payee

Creates a beneficiary for sending payments from the given account.

The financial institution may require the account owner to perform MFA when creating a payee. If MFA is required the response body from Teller will contain the property `connect_token`. The token is then used to initialize Teller Connect (see `connectToken` in the [Teller Connect Guide](/docs/guides/connect)), which will prompt the user with the steps required to save the payee. Your implementation must handle this case.

### Request Properties

-   `scheme` _(string)_ - `zelle` for Zelle payments.

-   `address` _(string)_ - The email address or cellphone number of the payment beneficiary.

-   `name` _(string)_ - The payment beneficiary's name.

-   `type` _(string)_ - Whether the payment beneficiary is a `person` or `business`.

```bash
curl -X POST https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payees \
  -u test_token_ky6igyqi3qxa4: \
  -H 'Content-Type: application/json' \
  -d '{
    "scheme": "zelle",
    "address": "jackson.lewis@teller.io",
    "name": "Jackson Lewis",
    "type": "person"
  }'
```

```json
// The financial institution requires the end-user
// to perform MFA to complete the payment
{
  "connect_token": "xxxxxxxxxxxxxx"
}
```

```json
{
  "scheme": "zelle",
  "address": "jackson.lewis@teller.io",
  "name": "Jackson Lewis",
  "type": "person",
  "account_id": "acc_oiin624kqjrg2mp2ea000",
  "links": {
    "account": "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000"
  }
}
```

***

## Discover Supported Payment Schemes

First, check the links collection in the [account entity](/docs/api/account/details#get-account-details). If the `payments` element is not present, the account does not support payment origination. If the `payments` element is present, send an `OPTIONS` request to the payments resource to see which payment schemes are supported.

Currently, only Zelle is supported. Additional payment schemes will be added in the future.

```bash
curl -X OPTIONS https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payments
  -u test_token_ky6igyqi3qxa4:
```

```json
{
  "schemes": [
    {
      "name": "zelle",
    }
  ]
}
```

***

## Initiate a Payment

Initiates a payment to the beneficiary from the given account.

The financial institution may require the account owner to perform MFA before executing the payment request. If MFA is required the response body from Teller will contain the property `connect_token`. The token is then used to initialize Teller Connect (see `connectToken` in the [Teller Connect Guide](/docs/guides/connect)), which will prompt the user with the steps required to execute the payment. Your implementation must handle this case.

This endpoint supports idempotent requests. Use the `Idempotency-Key` request header with a unique value per payment request. We store the key and keep the behavior associated to it for 72 hours.

### Request Properties

-   `amount` _(string)_ - The payment amount in dollars and cents (optional) as a string, e.g. "13.37", "10.00", "5".

-   `memo` _(string)_ - A short description of the nature of the payment.

-   `payee` _(object)_ - An object with the attributes of the payee. To make a payment to an existing payee, it's sufficient to specify the payee's `scheme` and `address` only. To make a payment to a new payee, specify all payee's attributes.

```bash
curl -X POST https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payments \
  -u test_token_ky6igyqi3qxa4: \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": "10.48",
    "memo": "Drinks",
    "payee": {
      "scheme": "zelle",
      "address": "jackson.lewis@teller.io"
    }
  }'
```

```bash
curl -X POST https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payments \
  -u test_token_ky6igyqi3qxa4: \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": "10.48",
    "memo": "Drinks",
    "payee": {
      "scheme": "zelle",
      "address": "jackson.lewis@teller.io",
      "name": "Jackson Lewis",
      "type": "person"
    }
  }'
```

```json
// The financial institution requires the end-user
// to perform MFA to complete the payment
{
  "connect_token": "xxxxxxxxxxxxxx"
}
```

```json
{
  "id": "zpay_o2iauakr4qme4v7uku000",
  "amount": "10.48",
  "memo": "Drinks",
  "reference": "GQ3C2MRQGIZC2MBXFUZDMLJVHEZDILKENFXG4ZLS",
  "date": "2023-09-04",
  "payee": {
    "scheme": "zelle",
    "type": "person",
    "name": "Jackson Lewis",
    "address": "jackson.lewis@teller.io",
  },
  "links": {
    "self": "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payments/zpay_o2iauakr4qme4v7uku000",
    "account": "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000"
  }
}
```

***

## List Payments

Returns a list of all payments that have been initiated via Teller API.

```bash
curl https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payments \
  -u test_token_ky6igyqi3qxa4:
```

```json
[
  {
    "id": "zpay_o2iauakr4qme4v7uku000",
    "amount": "10.48",
    "memo": "Drinks",
    "reference": "GQ3C2MRQGIZC2MBXFUZDMLJVHEZDILKENFXG4ZLS",
    "date": "2023-09-04",
    "payee": {
      "scheme": "zelle",
      "type": "person",
      "name": "Jackson Lewis",
      "address": "jackson.lewis@teller.io",
    },
    "links": {
      "self": "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payments/zpay_o2iauakr4qme4v7uku000",
      "account": "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000"
    }
  }
,
  ...
]
```

***

## Get Payment

Retrieve a specific payment by its id.

```bash
curl https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payments/zpay_o2iauakr4qme4v7uku000 \
  -u test_token_ky6igyqi3qxa4:
```

```json
{
  "id": "zpay_o2iauakr4qme4v7uku000",
  "amount": "10.48",
  "memo": "Drinks",
  "reference": "GQ3C2MRQGIZC2MBXFUZDMLJVHEZDILKENFXG4ZLS",
  "date": "2023-09-04",
  "payee": {
    "scheme": "zelle",
    "type": "person",
    "name": "Jackson Lewis",
    "address": "jackson.lewis@teller.io",
  },
  "links": {
    "self": "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000/payments/zpay_o2iauakr4qme4v7uku000",
    "account": "https://api.teller.io/accounts/acc_oiin624kqjrg2mp2ea000"
  }
}
```

---

## Institutions

Source: https://teller.io/docs/api/institutions.md

---

# Institutions

> **Note**
>
> This is a beta API and as such the interface is subject to change

An Institution represents a Financial Institution that is supported by Teller.

## Properties

-   `id` _(string)_ - Teller id of the institution.

-   `name` _(string)_ - Name of the institution.

-   `products` _(array)_ - List of Teller's products supported for the institution.

***

## List Institutions

Returns a list of all institutions supported by Teller. There is no
pagination currently. Doesn't require authentication.

```bash
curl https://api.teller.io/institutions
```

```json
[
  {
    "name": "Chase",
    "id": "chase",
    "products": [
      "verify",
      "balance",
      "transactions",
      "identity"
    ]
  },
  ...
]
```

---