"""Canonical Nexar support playbook: KB articles, SOP documents, and agent rules.

Seeded on API startup. Edit this file and restart the backend to reindex.
"""

SEED_USER = "system@nexar.ops"

CATEGORIES = [
    {
        "slug": "subscription",
        "name": "Subscription",
        "description": "Billing, plans, and Recurly subscription procedures",
    },
    {
        "slug": "returns",
        "name": "Returns",
        "description": "Device return and RMA procedures",
    },
    {
        "slug": "connectivity",
        "name": "Connectivity",
        "description": "Nexar Connect pairing and LTE connectivity",
    },
    {
        "slug": "hardware",
        "name": "Hardware",
        "description": "Hardware malfunction and warranty resolution",
    },
    {
        "slug": "classic-connectivity",
        "name": "Classic Connectivity",
        "description": "Nexar Classic app pairing and WiFi issues",
    },
    {
        "slug": "orders",
        "name": "Orders",
        "description": "Shopify and Amazon order, shipping, and cancellation procedures",
    },
    {
        "slug": "warranty",
        "name": "Warranty",
        "description": "Warranty eligibility and hardware replacement",
    },
]

KB_ARTICLES = [
    {
        "title": "Nexar Company Overview",
        "summary": "Who Nexar is, what we sell, and how internal support should represent the company.",
        "source_url": "https://www.getnexar.com",
        "markdown": """# Company

Nexar builds AI dash cams and connected-vehicle software for drivers and fleets. Support's job is to help customers with cameras, the Nexar app, Connect LTE, subscriptions, orders, and warranty — never to guess about account or device state.

# How we help

- Consumer customers buy on **Shopify** (Nexar shop) or **Amazon**.
- Fleet customers are a separate segment. Escalate fleet billing, installs, and multi-vehicle issues to the fleet queue.
- Internal tools in this agent talk to a simulation of Nexar systems (devices, Recurly, Shopify, Intercom). Treat tool results as source of truth.

# Tone

Be concise, calm, and practical. Use the customer's name when tools return it. Do not expose internal IDs, tokens, or raw JSON.
""",
    },
    {
        "title": "Nexar Product Line",
        "summary": "Nexar camera families, models, and which app or connectivity stack each one uses.",
        "source_url": "https://www.getnexar.com/products",
        "markdown": """# Product families

Nexar cameras fall into two families. Routing SOPs depend on this split.

# Classic cameras

Classic cameras pair over Bluetooth/Wi-Fi to the **Nexar Classic app**. They do not have an onboard LTE SIM.

- **Nexar Beam** — compact consumer Classic camera.
- **Nexar Pro** — Classic camera with more storage and cabin options.

Diagnostics for Classic pairing use `getClassicDiagnostic`. Do not run SIM triage on Classic cameras.

# Connect cameras

Connect cameras use **Nexar Connect** with an onboard LTE SIM and the Connect/V2 experience.

- **Nexar One** — flagship Connect camera; often paired with a rear camera.
- **Beam2 mini** (serial prefix B2-MINI) — compact Connect camera.

Connectivity issues use `getDeviceLookup` then `getSimTriage`. Hardware issues use `getDeviceHealth`.

# Rear camera

A rear (or interior-facing) camera is an accessory paired to a Connect primary camera. It is not sold as a standalone LTE device. If lookup shows `rear_camera.paired = no`, walk the customer through pairing in the app before replacing hardware.
""",
    },
    {
        "title": "Nexar Connect vs Classic",
        "summary": "How to tell Connect from Classic and which tools are allowed for each.",
        "source_url": "https://help.getnexar.com/connect-vs-classic",
        "markdown": """# Quick identification

- Serials like `NX-PRO-*` or older Beam units without LTE → **Classic**.
- Serials like `NX-ONE-*`, `NX-FLEET-*`, `B2-MINI-*` → **Connect**.
- If the customer mentions a turquoise LED, SIM, or LTE data cap → **Connect**.
- If they mention the Classic app, local Wi-Fi, or iOS Local Network permission → **Classic**.

# Tool restrictions

- Classic connectivity: `getClassicDiagnostic` only. Never `getSimTriage`, `reactivateSim`, or `createLTEQuota25GB`.
- Connect connectivity: `getDeviceLookup` then `getSimTriage`. Never `getClassicDiagnostic`.
- Hardware on either family: `getDeviceLookup` and `getDeviceHealth`. If `has_power_issues` is false, complete power troubleshooting before escalating.

# App names

- Classic → **Nexar Classic** app.
- Connect → **Nexar** / Connect app and **MyNexar** portal for subscription self-serve.
""",
    },
    {
        "title": "Subscription Plans and Billing",
        "summary": "Nexar plans, Recurly billing, invoice resend, and monthly vs annual switches.",
        "source_url": "https://help.getnexar.com/billing",
        "markdown": """# Plans

Typical consumer plans in this environment:

- **Nexar Basic Monthly** — cloud clips with a lower monthly price.
- **Nexar Pro Monthly** — full cloud + extra AI features.
- **Nexar Pro Annual** / **Nexar Annual Plan** — prepaid year; cheaper than 12 months of Pro Monthly.
- **Nexar Monthly Plan** — generic monthly after a plan switch.

# Billing system

Subscriptions are billed in **Recurly**, keyed by camera serial for Connect and by customer email for Classic/sim tools.

- Resend invoices: `getRecurlyInvoices` (optionally last N months).
- Change the billing email then resend: `updateRecurlyEmailAndSendInvoices`.
- Monthly → annual: `updateRecurlySubscriptionToAnnual`.
- Annual → monthly: `updateRecurlySubscriptionToMonthly`.

# Cancellation

Always look up the customer, list subscriptions, and get explicit confirmation before `cancel_subscription`. After a hardware return, remind the customer that an **activated Connect subscription** must also be cancelled in MyNexar if they no longer want to be billed.

# What support cannot do

Do not issue goodwill credits outside approved coupons (`createShopifyCoupon`, `getAccessoriesCoupon`). Do not invent invoice PDFs.
""",
    },
    {
        "title": "Warranty Policy",
        "summary": "Warranty window, in-warranty replacement, and out-of-warranty coupon options.",
        "source_url": "https://help.getnexar.com/warranty",
        "markdown": """# Coverage

Consumer cameras purchased from the **Nexar Shopify shop** carry a limited hardware warranty from the delivery date on the order. Warranty status is returned by `getDeviceLookup` / `getWarrantyEligibility` — never guess from the customer's memory of the purchase date.

# In warranty

If eligibility is active and the issue is a confirmed hardware fault:

1. Confirm the Shopify order number and camera model.
2. Call `getShopifyOrderItems` so the replacement SKU matches.
3. Create the replacement with `createShopifyReplacement`.
4. Do not also create a return RMA unless the SOP says to collect the old unit.

# Out of warranty

Offer a discount coupon via `createShopifyCoupon` (typical 15–25% off a replacement) or an accessory coupon via `getAccessoriesCoupon` for mounts, cables, and rear cameras. Do not promise a free replacement.

# Amazon purchases

Nexar cannot run Shopify warranty RMAs on Amazon orders. Direct the customer to Amazon returns/A-to-Z for the original purchase. We can still diagnose the camera and advise.
""",
    },
    {
        "title": "Returns and RMA Policy",
        "summary": "30-day returns, Shopify-only RMAs, and what happens after a device is sent back.",
        "source_url": "https://help.getnexar.com/returns",
        "markdown": """# Eligibility

Shopify orders may be returned within the window returned by `verifyReturnEligibility`. Amazon orders must be returned through Amazon — Nexar cannot create a prepaid label for them.

# Device vs order return

- **Device-centric** (customer has a serial, no order number): list devices, confirm serial, then `initiate_return`.
- **Order-centric** (customer has a Shopify order number): verify eligibility, optionally confirm shipping address, then `createReturnForOrder`. That creates a USPS prepaid label and RMA URL.

# After the RMA

Tell the customer to print the prepaid label, drop the package at USPS, and wait for inspection before a refund. If they already activated Nexar Connect, they must cancel the subscription in MyNexar to stop billing.

# Reasons we refuse

- Amazon channel
- Already fully refunded
- Outside the eligibility window (offer warranty path instead if hardware is faulty)
""",
    },
    {
        "title": "LTE Data and SIM Policy",
        "summary": "Connect SIM reactivation, 25GB LTE uplift, and when to escalate data issues.",
        "source_url": "https://help.getnexar.com/lte",
        "markdown": """# Who this applies to

Only **Connect** cameras (Nexar One, Beam2 mini, fleet Connect). Classic cameras have no SIM.

# Triage

Always `getDeviceLookup` then `getSimTriage`. Follow `recommended_action`:

- `reactivate_sim` → `reactivateSim`
- `uplift_25gb` → `createLTEQuota25GB` (monthly cap to 25GB)
- `escalate` → `ticketInternalNote` then `ticketEscalate`

Optional: `getSimData` to explain usage to the customer.

# What we tell customers

LTE is for camera uploads and live features, not a phone hotspot. Repeated cap hits may mean a faulty unit (hardware SOP) or a fleet vehicle that needs a fleet data plan.

# Fleet

Fleet Connect devices: do not apply consumer 25GB uplifts as a permanent fix. Escalate to the fleet queue after documenting triage.
""",
    },
    {
        "title": "Rear Camera Support",
        "summary": "Pairing, interior-facing mode, and when a rear camera is out of scope for LTE tools.",
        "source_url": "https://help.getnexar.com/rear-camera",
        "markdown": """# Prerequisites

A rear camera requires a working **Connect primary** camera, the Nexar app, and Bluetooth/Wi-Fi during pairing. Lookup fields: `rear_camera.paired` and `rear_camera.interior_facing`.

# Pairing

1. Confirm the primary serial with `getDeviceLookup`.
2. If the primary is Classic, rear LTE accessories are not supported — sell or ship a Connect-compatible rear unit only with Connect primaries.
3. If unpaired, ask the customer to start pairing from the app (Add rear camera). Keep the cameras 1–2 meters apart, engine on, and location permission set to Always.
4. Interior-facing mode is a software toggle after pairing; it is not a separate SKU.

# Hardware

If the primary is healthy and pairing still fails after a power cycle, treat the rear unit under the Hardware Malfunction SOP and warranty path.
""",
    },
    {
        "title": "Orders Shipping and Purchase Channels",
        "summary": "Shopify vs Amazon, tracking, address changes, and order cancellation rules.",
        "source_url": "https://help.getnexar.com/orders",
        "markdown": """# Channels

- **Shopify** (Nexar shop): we can look up status, change the shipping address on unfulfilled orders, cancel unfulfilled orders, and create RMAs.
- **Amazon**: we can identify the channel from an order number or customer message (`ticketMessageResponse` / `getDeviceOrder`) but we cannot cancel, relabel, or refund Amazon orders. Send the customer to Amazon order history.

# Status

Use `getOrderStatusShopify` for fulfillment, delivery, tracking, and return/refund flags. Typical fulfillment values: unfulfilled, fulfilled, cancelled. Delivery may be IN_TRANSIT or DELIVERED.

# Address change

Only unfulfilled Shopify orders. Collect the new address, then `changeAddressShopify`.

# Cancellation

Unfulfilled Shopify only, via `cancelShopifyOrder`. If the order is already fulfilled, use the return SOP instead.
""",
    },
    {
        "title": "Support Hours and Escalation",
        "summary": "When to stay in self-serve tools vs escalate to a human queue or Jira.",
        "source_url": "https://help.getnexar.com/escalation",
        "markdown": """# Stay in the agent

Diagnostic lookups, SIM reactivation, LTE uplift, invoice resend, eligible Shopify RMAs, and in-warranty replacements that tools can complete.

# Escalate (`ticketEscalate`)

- Fleet accounts
- Safety incidents / collisions (do not diagnose crash video here; route to the safety queue)
- Confirmed hardware fault with `has_power_issues` after troubleshooting
- SIM triage `recommended_action = escalate`
- Angry customers asking for a supervisor
- Anything involving legal, insurance, or law-enforcement requests

Always write `ticketInternalNote` with serial, order number, tools already run, and the last customer-facing summary before escalating.

# Jira

Use `jiraCreateIssue` only for back-office bugs (app crash loops, catalog defects), not for ordinary support tickets.

# Resolve without a tool action

Spam, duplicate outreach, or a customer who already confirmed they are done: `ticketResolve` with a short reason.
""",
    },
]

AGENT_RULES = [
    {
        "category": "business_context",
        "content": "Nexar sells AI dash cams (Classic: Beam/Pro; Connect: Nexar One and Beam2 mini) plus cloud subscriptions billed in Recurly. Consumer orders come from Shopify or Amazon.",
    },
    {
        "category": "business_context",
        "content": "Classic cameras use the Nexar Classic app (Bluetooth/Wi-Fi). Connect cameras use LTE SIM + Connect app. Never mix Classic diagnostic tools with Connect SIM tools.",
    },
    {
        "category": "escalations",
        "content": "Escalate fleet customers, safety/collision cases, legal requests, and SIM triage recommended_action=escalate. Write an internal note with serial, order number, and tools already used before ticketEscalate.",
    },
    {
        "category": "escalations",
        "content": "Amazon orders cannot be cancelled, relabeled, or refunded by Nexar. Direct those customers to Amazon. Shopify-only tools must not be used on Amazon channel orders.",
    },
    {
        "category": "response_tone_style",
        "content": "Write short Markdown answers. Lead with the outcome, then bullets for next steps. Never dump JSON, tokens, or internal identifiers.",
    },
    {
        "category": "agent_capabilities",
        "content": "Search the knowledge base for policy/product questions. Search SOP processes for multi-step work (returns, SIM, hardware, warranty, billing). Follow a matched SOP's tools only.",
    },
    {
        "category": "agent_capabilities",
        "content": "Never invent device health, order status, or warranty dates. If a tool is required and a parameter is missing, ask for it. Do not claim an action succeeded without a successful tool result.",
    },
]


def _step(step_id: str, step_type: str, instruction: str, tool: str | None = None) -> dict:
    payload = {"id": step_id, "type": step_type, "instruction": instruction}
    if tool:
        payload["tool"] = tool
    return payload


SOP_DOCUMENTS = [
    {
        "category_slug": "subscription",
        "title": "Subscription Handling",
        "summary": "Look up a Nexar customer, review Recurly plans, cancel or create a subscription.",
        "raw_text": """# Subscription Operations

## Cancel subscription
When a customer asks to cancel their subscription or stop billing:
1. Ask for the customer email and confirm you have the right account.
2. Call @lookup_customer_by_email to verify the customer exists.
3. Call @list_subscriptions to show active subscriptions.
4. Ask the user which subscription to cancel and get explicit confirmation.
5. Call @cancel_subscription with the subscription_id.
6. Tell the user a confirmation message was written to the Messages outbox.

Triggers: cancel my subscription, stop my subscription, cancel nexar plan

## Create or get subscription
When a customer wants to start a plan or check status:
1. Ask for the customer email.
2. Call @lookup_customer_by_email.
3. Call @list_subscriptions to show current plans.
4. If they want a new plan, confirm plan name then call @create_subscription.
5. Summarize the result for the user.
""",
        "processes": [
            {
                "process_key": "cancel_subscription",
                "title": "Cancel subscription",
                "description": "Verify customer, list plans, confirm, and cancel via internal tools.",
                "trigger_phrases": [
                    "cancel my subscription",
                    "stop my subscription",
                    "cancel nexar plan",
                    "stop billing",
                ],
                "tools": ["lookup_customer_by_email", "list_subscriptions", "cancel_subscription"],
                "steps": [
                    _step("ask_email", "ask_user", "Ask for the customer email"),
                    _step("lookup", "call_tool", "Verify customer", "lookup_customer_by_email"),
                    _step("list", "call_tool", "List subscriptions", "list_subscriptions"),
                    _step("confirm", "confirm", "Confirm which subscription to cancel"),
                    _step("cancel", "call_tool", "Cancel the subscription", "cancel_subscription"),
                    _step("inform", "inform", "Confirm cancellation and that a message was logged"),
                ],
            },
            {
                "process_key": "create_or_view_subscription",
                "title": "Create or view subscription",
                "description": "Look up a customer and create or review subscriptions.",
                "trigger_phrases": ["create a subscription", "start a plan", "get my subscription"],
                "tools": ["lookup_customer_by_email", "list_subscriptions", "create_subscription"],
                "steps": [
                    _step("ask_email", "ask_user", "Ask for the customer email"),
                    _step("lookup", "call_tool", "Verify customer", "lookup_customer_by_email"),
                    _step("list", "call_tool", "List current subscriptions", "list_subscriptions"),
                    _step("create", "call_tool", "Create subscription if requested", "create_subscription"),
                ],
            },
        ],
    },
    {
        "category_slug": "returns",
        "title": "Return My Device",
        "summary": "Identify a customer's cameras and start a device-level return.",
        "raw_text": """# Device Return Operations

## Return my device
When a customer wants to return a dash cam:
1. Ask for the customer email.
2. Call @lookup_customer_by_email.
3. Call @list_customer_devices and present the devices.
4. Ask which serial number to return and confirm the reason.
5. Optionally call @lookup_device for that serial.
6. After confirmation, call @initiate_return.
7. Tell the user a return confirmation was logged in Messages.

Triggers: return my device, return my dash cam, start an RMA, send device back
""",
        "processes": [
            {
                "process_key": "return_device",
                "title": "Return my device",
                "description": "Identify customer devices, confirm, and initiate a return.",
                "trigger_phrases": [
                    "return my device",
                    "return my dash cam",
                    "start an RMA",
                    "send device back",
                ],
                "tools": [
                    "lookup_customer_by_email",
                    "list_customer_devices",
                    "lookup_device",
                    "initiate_return",
                ],
                "steps": [
                    _step("ask_email", "ask_user", "Ask for the customer email"),
                    _step("lookup", "call_tool", "Verify customer", "lookup_customer_by_email"),
                    _step("list", "call_tool", "List devices", "list_customer_devices"),
                    _step("confirm", "confirm", "Confirm serial number and return reason"),
                    _step("return", "call_tool", "Initiate the return", "initiate_return"),
                    _step("inform", "inform", "Confirm return started and message logged"),
                ],
            }
        ],
    },
    {
        "category_slug": "classic-connectivity",
        "title": "SOP - Nexar Classic App Connectivity & Pairing",
        "summary": "Pairing and permission diagnostics for Classic cameras using getClassicDiagnostic.",
        "raw_text": """# Nexar Classic App Connectivity

When a Classic camera (Beam, Pro) will not pair or stay connected to the Classic app:
1. Collect email or phone.
2. Call @getClassicDiagnostic.
3. Fix the first failing permission (Location Always, Precise Location, Local Network, Bluetooth, storage).
4. Do not use Connect SIM tools.
""",
        "processes": [
            {
                "process_key": "classic_app_connectivity",
                "title": "Nexar Classic App Connectivity",
                "description": "Diagnose Classic app pairing using permission flags. Never use SIM tools.",
                "trigger_phrases": [
                    "classic app",
                    "won't pair",
                    "camera not pairing",
                    "nexar pro wifi",
                    "local network permission",
                    "bluetooth pairing",
                ],
                "tools": ["getClassicDiagnostic", "getDeviceLookup"],
                "steps": [
                    _step("identify", "ask_user", "Ask for customer email or phone if not already provided"),
                    _step("lookup", "call_tool", "Confirm the camera is Classic if a serial or email is known", "getDeviceLookup"),
                    _step("diag", "call_tool", "Run Classic app permission diagnostics", "getClassicDiagnostic"),
                    _step(
                        "coach",
                        "inform",
                        "Walk through the first failing flag: Location Always, Precise Location, Local Network (iOS), Bluetooth, storage, or notifications",
                    ),
                    _step("retry", "ask_user", "Ask the customer to force-quit the Classic app, toggle Bluetooth, and retry pairing with the camera powered"),
                    _step(
                        "escalate",
                        "inform",
                        "If camera_paired stays false after permissions are healthy, switch to the Hardware Malfunction SOP — do not run getSimTriage",
                    ),
                ],
            }
        ],
    },
    {
        "category_slug": "connectivity",
        "title": "SOP - Connectivity for Nexar Connect V2",
        "summary": "LTE/SIM triage for Connect cameras: lookup, sim triage, reactivate or 25GB uplift.",
        "raw_text": """# Sim Triage

Connect camera connectivity (Nexar One, Beam2 mini):
1. Call @getDeviceLookup with serial, email, or phone.
2. Call @getSimTriage with the serial.
3. Follow recommended_action: reactivate_sim → @reactivateSim; uplift_25gb → @createLTEQuota25GB; escalate → note + @ticketEscalate.
""",
        "processes": [
            {
                "process_key": "sim_triage",
                "title": "Sim Triage",
                "description": "Connect LTE connectivity: lookup, triage, then reactivate SIM, uplift data, or escalate.",
                "trigger_phrases": [
                    "won't connect",
                    "lte",
                    "sim not working",
                    "no live view",
                    "turquoise light",
                    "data cap",
                    "nexar one not connecting",
                ],
                "tools": [
                    "getDeviceLookup",
                    "getSimTriage",
                    "getSimData",
                    "reactivateSim",
                    "createLTEQuota25GB",
                    "ticketInternalNote",
                    "ticketEscalate",
                ],
                "steps": [
                    _step("collect", "ask_user", "Collect serial, email, or phone if missing"),
                    _step("lookup", "call_tool", "Look up the Connect camera", "getDeviceLookup"),
                    _step("triage", "call_tool", "Run SIM triage", "getSimTriage"),
                    _step("usage", "call_tool", "Optionally pull SIM usage to explain a cap", "getSimData"),
                    _step("reactivate", "call_tool", "If recommended_action is reactivate_sim", "reactivateSim"),
                    _step("uplift", "call_tool", "If recommended_action is uplift_25gb", "createLTEQuota25GB"),
                    _step("note", "call_tool", "If recommended_action is escalate, write an internal note", "ticketInternalNote"),
                    _step("escalate", "call_tool", "Escalate to the connectivity queue", "ticketEscalate"),
                ],
            }
        ],
    },
    {
        "category_slug": "hardware",
        "title": "SOP - Hardware Malfunction",
        "summary": "Power, recording, and hardware faults: health check, troubleshooting, then warranty or escalate.",
        "raw_text": """# Hardware Malfunction

When a camera has power, battery, red LED, SD, or recording failures:
1. Call @getDeviceLookup and @getDeviceHealth.
2. If has_power_issues is false, complete power troubleshooting (cable, fuse, 12V, reboot) before escalating.
3. In-warranty Shopify hardware → warranty replacement SOP. Otherwise escalate with an internal note.
""",
        "processes": [
            {
                "process_key": "hardware_malfunction",
                "title": "Hardware Malfunction",
                "description": "Confirm hardware health. Troubleshoot power before escalating when has_power_issues is false.",
                "trigger_phrases": [
                    "not turning on",
                    "red light",
                    "blinking red",
                    "battery swollen",
                    "not recording",
                    "sd card error",
                    "defective camera",
                    "hardware issue",
                ],
                "tools": [
                    "getDeviceLookup",
                    "getDeviceHealth",
                    "getValidateSerial",
                    "ticketInternalNote",
                    "ticketEscalate",
                ],
                "steps": [
                    _step("collect", "ask_user", "Collect serial or email"),
                    _step("validate", "call_tool", "Validate the serial if provided", "getValidateSerial"),
                    _step("lookup", "call_tool", "Look up warranty and model", "getDeviceLookup"),
                    _step("health", "call_tool", "Pull device health", "getDeviceHealth"),
                    _step(
                        "power",
                        "inform",
                        "If has_power_issues is false: hard reboot, confirm 12V accessory power / fuse, reseat USB-C or OBD power, try a known-good cable. Do not escalate yet.",
                    ),
                    _step(
                        "irq",
                        "inform",
                        "If irq or persistent recording/SD faults remain after reboot, treat as confirmed hardware fault",
                    ),
                    _step("note", "call_tool", "Document serial, health flags, and troubleshooting", "ticketInternalNote"),
                    _step(
                        "next",
                        "inform",
                        "If Shopify warranty is active, continue with warranty replacement. Otherwise escalate or offer an out-of-warranty coupon.",
                    ),
                ],
            }
        ],
    },
    {
        "category_slug": "orders",
        "title": "Shopify Order Status and Shipping",
        "summary": "Look up Shopify fulfillment and tracking; change address or cancel only when unfulfilled.",
        "raw_text": """# Order status
Use @getOrderStatusShopify. Amazon orders cannot be managed here.

## Change address
Unfulfilled Shopify only: @changeAddressShopify.

## Cancel order
Unfulfilled Shopify only: @cancelShopifyOrder. Fulfilled orders use the return SOP.
""",
        "processes": [
            {
                "process_key": "order_status_shipping",
                "title": "Check Shopify order status",
                "description": "Look up fulfillment, tracking, and delivery. Identify Amazon vs Shopify first.",
                "trigger_phrases": [
                    "where is my order",
                    "tracking number",
                    "shipping status",
                    "has it shipped",
                    "delivery status",
                ],
                "tools": [
                    "ticketMessageResponse",
                    "getDeviceOrder",
                    "getOrderStatusShopify",
                    "getOrderShippingAddressAndPhoneNumber",
                ],
                "steps": [
                    _step("channel", "call_tool", "If the customer pasted a message or order number, identify the channel", "ticketMessageResponse"),
                    _step("status", "call_tool", "Get Shopify order status", "getOrderStatusShopify"),
                    _step("address", "call_tool", "If they ask where it is going, fetch the shipping address", "getOrderShippingAddressAndPhoneNumber"),
                    _step("amazon", "inform", "If the channel is Amazon, explain Nexar cannot change Amazon shipments"),
                ],
            },
            {
                "process_key": "change_shipping_address",
                "title": "Change Shopify shipping address",
                "description": "Update address on an unfulfilled Shopify order.",
                "trigger_phrases": ["wrong address", "change shipping address", "update delivery address"],
                "tools": ["getOrderStatusShopify", "changeAddressShopify"],
                "steps": [
                    _step("status", "call_tool", "Confirm the order is unfulfilled", "getOrderStatusShopify"),
                    _step("collect", "ask_user", "Collect the full new address"),
                    _step("update", "call_tool", "Submit the address change", "changeAddressShopify"),
                ],
            },
            {
                "process_key": "cancel_shopify_order",
                "title": "Cancel unfulfilled Shopify order",
                "description": "Cancel a Shopify order that has not shipped.",
                "trigger_phrases": ["cancel my order", "i ordered by mistake", "stop the shipment"],
                "tools": ["getOrderStatusShopify", "cancelShopifyOrder"],
                "steps": [
                    _step("status", "call_tool", "Confirm unfulfilled Shopify", "getOrderStatusShopify"),
                    _step("confirm", "confirm", "Confirm cancellation with the customer"),
                    _step("cancel", "call_tool", "Cancel the order", "cancelShopifyOrder"),
                ],
            },
        ],
    },
    {
        "category_slug": "returns",
        "title": "Shopify Order Return",
        "summary": "Verify return eligibility and create a prepaid USPS RMA for a Shopify order.",
        "raw_text": """# Return a Shopify order
1. @verifyReturnEligibility
2. Confirm reason
3. @createReturnForOrder
Amazon orders must go through Amazon.
""",
        "processes": [
            {
                "process_key": "shopify_order_return",
                "title": "Create Shopify return",
                "description": "Eligibility check then prepaid USPS RMA for a Shopify order.",
                "trigger_phrases": [
                    "return my order",
                    "send it back",
                    "prepaid return label",
                    "not as described",
                ],
                "tools": [
                    "verifyReturnEligibility",
                    "getOrderShippingAddressAndPhoneNumber",
                    "createReturnForOrder",
                ],
                "steps": [
                    _step("eligible", "call_tool", "Verify Shopify return eligibility", "verifyReturnEligibility"),
                    _step("reason", "ask_user", "Confirm the return reason"),
                    _step("create", "call_tool", "Create the RMA and prepaid label", "createReturnForOrder"),
                    _step(
                        "inform",
                        "inform",
                        "Give tracking, RMA URL, USPS drop-off, and remind them to cancel Connect billing in MyNexar if the camera was activated",
                    ),
                ],
            }
        ],
    },
    {
        "category_slug": "warranty",
        "title": "Warranty Hardware Replacement",
        "summary": "Confirm Shopify warranty, match line items, replace in-warranty or issue an out-of-warranty coupon.",
        "raw_text": """# Warranty replacement
@getWarrantyEligibility then @getShopifyOrderItems then @createShopifyReplacement.
Out of warranty: @createShopifyCoupon or @getAccessoriesCoupon.
""",
        "processes": [
            {
                "process_key": "warranty_replacement",
                "title": "Replace in-warranty hardware",
                "description": "Shopify warranty replacement after a confirmed hardware fault.",
                "trigger_phrases": [
                    "warranty replacement",
                    "replace my camera",
                    "defective unit",
                    "swap the dash cam",
                ],
                "tools": [
                    "getDeviceLookup",
                    "getWarrantyEligibility",
                    "getShopifyOrderItems",
                    "createShopifyReplacement",
                    "createShopifyCoupon",
                    "getAccessoriesCoupon",
                ],
                "steps": [
                    _step("lookup", "call_tool", "Look up the device and purchase channel", "getDeviceLookup"),
                    _step("elig", "call_tool", "Check warranty eligibility", "getWarrantyEligibility"),
                    _step("items", "call_tool", "If in warranty, fetch Shopify line items", "getShopifyOrderItems"),
                    _step("replace", "call_tool", "Create the replacement RMA", "createShopifyReplacement"),
                    _step("coupon", "call_tool", "If out of warranty, offer a replacement coupon", "createShopifyCoupon"),
                    _step("accessory", "call_tool", "If they need a mount or cable, issue an accessory coupon", "getAccessoriesCoupon"),
                ],
            }
        ],
    },
    {
        "category_slug": "subscription",
        "title": "Billing Invoices and Plan Changes",
        "summary": "Resend Recurly invoices, update billing email, and switch monthly vs annual.",
        "raw_text": """# Invoices
@getRecurlyInvoices or @updateRecurlyEmailAndSendInvoices.

# Plan switch
@updateRecurlySubscriptionToAnnual or @updateRecurlySubscriptionToMonthly.
""",
        "processes": [
            {
                "process_key": "resend_invoices",
                "title": "Resend Recurly invoices",
                "description": "Send past invoices, optionally after updating billing email.",
                "trigger_phrases": ["send my invoices", "I need receipts", "billing email is wrong"],
                "tools": ["getRecurlyInvoices", "updateRecurlyEmailAndSendInvoices"],
                "steps": [
                    _step("serial", "ask_user", "Ask for the camera serial if missing"),
                    _step("send", "call_tool", "Resend invoices to the email on file", "getRecurlyInvoices"),
                    _step("update", "call_tool", "If the billing email is wrong, update it and resend", "updateRecurlyEmailAndSendInvoices"),
                ],
            },
            {
                "process_key": "switch_plan_term",
                "title": "Switch monthly and annual plans",
                "description": "Move a Recurly subscription between monthly and annual.",
                "trigger_phrases": ["switch to annual", "go monthly", "change my plan term"],
                "tools": ["updateRecurlySubscriptionToAnnual", "updateRecurlySubscriptionToMonthly"],
                "steps": [
                    _step("confirm", "confirm", "Confirm serial and which direction (monthly vs annual)"),
                    _step("annual", "call_tool", "If they want annual", "updateRecurlySubscriptionToAnnual"),
                    _step("monthly", "call_tool", "If they want monthly", "updateRecurlySubscriptionToMonthly"),
                ],
            },
        ],
    },
]
