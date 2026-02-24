The OXXO Reconciliation Nightmare: Untangle UrbanStyle's Cash Payment Chaos
The Scenario
UrbanStyle is a fast-growing fashion e-commerce platform operating across Mexico and Colombia. Like many Latin American merchants, they accept cash-based payment methods alongside traditional card payments—specifically OXXO (Mexico) and Efecty (Colombia). These payment methods are wildly popular: 40% of UrbanStyle's customers prefer to pay with cash at convenience stores.

But there's a problem. A big one.

Last week, UrbanStyle's finance team discovered that 18% of their cash payments are either missing, mismatched, or incorrectly reconciled. Customers are complaining that they paid at a store three days ago but their order is still marked "pending payment." Meanwhile, UrbanStyle's warehouse is shipping orders that were never actually paid for. The CFO is furious, and the customer support queue has grown 400% in two weeks.

UrbanStyle processes about 2,000 cash payment transactions per week through Yuno. Each transaction goes through multiple states over several days, and the data is scattered across multiple systems. They've asked Yuno to build a reconciliation service that can identify mismatches, anomalies, and stuck transactions across their payment lifecycle.

You've been assigned to prototype this solution. Your goal is to build a backend service and API that ingests payment data from multiple sources, identifies reconciliation issues, and exposes the findings through a queryable interface.

Domain Background: Understanding Cash-Based Payment Methods
If you've never worked with cash payments in Latin America, here's what you need to know:

What are OXXO and Efecty?
OXXO (Mexico) and Efecty (Colombia) are offline cash payment methods. Here's how they work:

Customer checks out online: The customer selects "Pay with OXXO" or "Pay with Efecty" at checkout
Payment voucher is generated: The system generates a voucher with a unique payment reference code and barcode
Customer goes to a physical store: The customer has 48-72 hours to visit an OXXO or Efecty location (convenience stores found on nearly every corner)
Customer pays in cash: The store cashier scans the barcode, the customer pays in cash, and the store transmits the payment confirmation
Merchant receives confirmation: Usually within minutes to hours, but sometimes up to 24-48 hours later
Payment Lifecycle States
Unlike card payments (which are instant), cash payments go through multiple states:

PENDING: Voucher generated, waiting for customer to pay at store
PAID: Store has confirmed payment received (money collected from customer)
CONFIRMED: Payment processor has validated and confirmed the transaction
COMPLETED: Funds have been settled to the merchant's account
EXPIRED: Customer never paid within the time window (48-72 hours)
CANCELLED: Merchant or customer cancelled the order before payment
The Reconciliation Challenge
Cash payments create reconciliation headaches because:

Time lag: Payment confirmation can arrive hours or days after the customer pays
Multiple data sources: Payment data comes from the voucher generation system, the store network, the payment processor, and the merchant's order system
Human error: Store clerks sometimes scan the wrong barcode or enter amounts incorrectly
Network issues: Store networks in remote areas may have delayed transmission
Fraud: Fake vouchers, duplicate payments, or tampered barcodes
What is Reconciliation?
Reconciliation is the process of matching and verifying transactions across multiple systems to ensure they're consistent and accurate. In this context, you need to:

Match voucher generation records with payment confirmation records
Identify transactions stuck in limbo (paid but never confirmed, or confirmed but never completed)
Flag mismatches (e.g., voucher amount doesn't match paid amount)
Detect anomalies (e.g., voucher expired but payment was received anyway)
The Challenge
Build a backend reconciliation service that:

Ingests payment data from multiple sources (voucher generation events, payment confirmations, settlement records)
Identifies reconciliation issues using a set of business rules
Exposes findings via a REST or GraphQL API that UrbanStyle's finance team can query
Functional Requirements
1. Multi-Source Data Ingestion
Your service must be able to ingest payment transaction data from three simulated sources:

Voucher System: Records of payment vouchers generated (when customer selects OXXO/Efecty at checkout)
Payment Processor: Confirmation events when customers actually pay at stores
Settlement System: Records of funds transferred to merchant account
Each record will have a unique transaction ID, but the timing and completeness of data across sources will vary (this is the reconciliation problem). Your service should store or process this data in a way that allows cross-referencing.

What "done" looks like: Your service can accept transaction data via API endpoints, file upload, or any mechanism you choose. It should handle at least these fields per record: transaction ID, timestamp, status, amount, currency, payment method, and source system.

2. Issue Detection Engine
Implement logic to detect at least these five types of reconciliation issues:

Orphaned Payments: Payment confirmation exists but no voucher generation record found
Stuck Pending: Voucher created more than 72 hours ago, still in PENDING state, no payment confirmation received
Amount Mismatch: Voucher amount doesn't match the paid amount (tolerance: ±1% for currency conversion rounding)
Zombie Completions: Transaction marked COMPLETED but never went through CONFIRMED state
Post-Expiration Payments: Payment received after voucher expiration timestamp
For each detected issue, your system should capture: transaction ID(s) involved, issue type, severity (low/medium/high), timestamp detected, and a human-readable description.

What "done" looks like: Given a set of test transactions with intentional mismatches and anomalies, your service correctly identifies all five issue types.

3. Queryable Reconciliation API
Expose an API (REST or GraphQL) that allows UrbanStyle's finance team to:

Retrieve all detected issues, with filtering by issue type, severity, date range, and payment method
Get details for a specific transaction ID across all source systems
View summary statistics: total issues by type, total amount at risk, percentage of transactions with issues
What "done" looks like: A reviewer can use Postman, curl, or a GraphQL client to query your API and retrieve issue data in a structured format (JSON/XML). The API should have at least 3-4 endpoints/queries that cover the use cases above.

Stretch Goals (Partial Completion Expected)
If you have time, consider implementing:

Auto-resolution suggestions: For certain issue types (e.g., small amount mismatches), suggest an automatic resolution action
Batch reconciliation: Accept a large file of transactions and process them asynchronously, returning a job ID that can be polled for status
Trend detection: Identify if certain payment methods, time periods, or stores have higher issue rates
Webhook notifications: Send alerts when high-severity issues are detected
You are NOT expected to complete all stretch goals. Focus on a solid implementation of the core requirements first.

Test Data
To develop and demonstrate your solution, you'll need simulated transaction data. You should generate or mock this yourself (AI tools are perfect for this). Your test dataset should include:

At least 300 transaction records across the three source systems (voucher, payment processor, settlement)
Mix of payment methods: OXXO (Mexico, MXN currency) and Efecty (Colombia, COP currency)
Mix of states: PENDING, PAID, CONFIRMED, COMPLETED, EXPIRED, CANCELLED
Realistic timestamps: Voucher generation → payment confirmation (0-48 hours later) → settlement (1-3 days later)
At least 30-40 transactions with intentional issues representing all five issue types listed above (orphaned payments, stuck pending, amount mismatches, zombie completions, post-expiration payments)
Some clean transactions with no issues (the majority should be clean—issues should be the exception, not the rule)
Make sure your test data includes edge cases: same-day settlements, weekend delays, currency rounding differences, and transactions near the expiration threshold.

Acceptance Criteria
Your submission is complete when:

✅ Your service can ingest transaction data from simulated sources
✅ Running your issue detection logic against test data identifies all five issue types correctly
✅ A reviewer can query your API to retrieve issues, transaction details, and summary statistics
✅ Your code includes a README with: setup instructions, how to load test data, how to run the service, and example API calls
✅ You can demo the service working end-to-end (ingest data → detect issues → query via API)
Notes
Choose your own stack: Use any backend language/framework you're comfortable with (Node.js, Python, Go, Java, Ruby, etc.)
Data storage: Use any approach you like—in-memory, SQLite, Postgres, JSON files, etc. Focus on logic over infrastructure.
No UI required: This is a backend challenge. A simple API is sufficient. (But if you want to build a minimal dashboard as a stretch goal, go for it!)
AI tools encouraged: Use Claude, Cursor, Copilot, or any coding assistant. This challenge is scoped to be achievable in 2 hours with AI help.
Document your decisions: In your README, briefly explain your approach to issue detection and any trade-offs you made.
Good luck! 🚀
