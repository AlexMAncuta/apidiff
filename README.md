apidiff — arhitectură & workflow

API Breaking-Change Assistant
Un agent ADK compară două specificații OpenAPI, decide determinist ce s-a stricat pentru clienți, iar Gemini explică verdictul în limbaj natural. Python decide, Java generează datele de test, Terraform provizionează infrastructura.

Python 3.11 · ADK
Gemini 2.5 Flash · Vertex AI
Java 21 · Spring Boot 3
Cloud Run · Cloud Storage
Terraform
Problema
Orice echipă de backend strică din când în când clienți existenți printr-un API nou, fără să-și dea seama. Nu din neglijență — diff-ul text dintre două specificații OpenAPI are sute de linii, majoritatea zgomot, și nimeni nu-l citește rând cu rând înainte de fiecare release.

Cele mai periculoase schimbări arată nevinovate: un required = false devenit required = true, sau un Double devenit BigDecimal. Un diff text arată ambele modificări identic cu oricare alta — dar ambele pică producția.

Ce rezolvă acest proiect: compară automat două versiuni ale unui API și spune, determinist, care schimbări sunt breaking, warning sau safe — și de ce, în termeni de ce pățește exact un client existent.

Exemple de endpoint-uri (versiunea de bază, v1)
API-ul de test — un mic Spring Boot cu produse — expune 5 endpoint-uri. Fiecare are propriile variabile de intrare/ieșire.

Endpoint	Variabile primite	Ce întoarce
GET /api/products	category (opțional) — enum: ELECTRONICS, CLOTHING, FOOD, BOOKS	Product[]
GET /api/products/{id}	id (path, obligatoriu) — integer	Product
POST /api/products	body: Product — id, name, sku, description, price (double), category, available	Product
PUT /api/products/{id}	id (path) + body: Product	Product
DELETE /api/products/{id}	id (path, obligatoriu) — integer	200 OK
Ce schimbă v2 — exact ce vrea proiectul să detecteze
Aceleași endpoint-uri, după trei modificări plantate deliberat în cod Java. Fiecare pare o modificare minoră. Fiecare strică toți clienții existenți care făceau exact ce era permis în v1.

Un endpoint dispare complet
ENDPOINT_REMOVED
- DELETE /api/products/{id}
Orice client care mai apelează DELETE primește 404 imediat după deploy.

Un parametru opțional devine obligatoriu + o valoare de enum dispare
PARAM_NOW_REQUIRED
PARAM_ENUM_VALUE_REMOVED
- @RequestParam(required = false) Category category;  // enum: ELECTRONICS, CLOTHING, FOOD, BOOKS
+ @RequestParam(required = true)  Category category;  // enum: ELECTRONICS, CLOTHING, FOOD
Orice client care omitea "category" — comportament valid în v1 — primește acum 400. Iar dacă trimitea "BOOKS", primește 400 chiar dacă respecta contractul vechi.

Tipul unui câmp de răspuns se schimbă + un câmp dispare
RESPONSE_FIELD_TYPE_CHANGED
RESPONSE_FIELD_REMOVED
- private Double price;        // "type": "number", "format": "double"
+ private BigDecimal price;    // "type": "number"  ← format dispare, type rămâne "number"
- private String description;
Un diff text pe JSON nu vede diferența — ambele au "type": "number". Doar format s-a schimbat, dar un client tipizat (ex. deserializare strictă) eșuează. "description" citit ca null, apoi crash mai departe, departe de cauza reală.

1. Componentele sistemului
api-mock/ (Java) generează specificațiile de test rulând local. api-diff-python/ este singura parte care rulează efectiv în cloud — restul e infrastructură sau date de intrare.

terraform/

api-diff-python/ — singura parte deployată

local dev

producție

identitate rulare

găzduiește

api-mock/ (Java 21, Spring Boot 3)Product + Category + springdoc-openapi

mvn spring-boot:runcurl /v3/api-docs > openapi-vN.json

Utilizator

ADK Agentapi_breaking_change_assistant

Gemini 2.5 Flash(Vertex AI)

AssistantTools5 tool-uri

normalizer.py + comparator.pyregulile deterministe

KnowledgeProvider

knowledge/*.json + *.md

Cloud Storagebucket knowledge

terraform apply

Service Accountapi-diff-runner

Cloud Runapi-diff-assistant

2. Fluxul unei întrebări
Agentul nu decide niciodată singur dacă o schimbare strică ceva — apelează compare_api_versions, primește un verdict gata calculat, și doar îl explică. Așa e impus în prompts.py.

comparator.py
AssistantTools
Gemini 2.5 Flash
ADK Agent
comparator.py
AssistantTools
Gemini 2.5 Flash
ADK Agent
Utilizator
"Compară v1 cu v2, pot face upgrade?"
prompt + system instructions
cere tool list_api_versions
list_api_versions()
[openapi-v1.json, openapi-v2.json, ...]
rezultatul tool-ului
cere tool compare_api_versions(v1, v2)
compare_api_versions()
compare_specs(old, new)
findings [BREAKING / WARNING / SAFE]
summary + findings
rezultatul tool-ului
cere tool search_documents(regulă)
search_documents("PARAM_NOW_REQUIRED")
extrase din breaking-changes.md
rezultatul tool-ului
răspuns final, în limbaj natural
verdict + grupare pe cauză + migrare
Utilizator
3. Pipeline-ul de comparație
Specificațiile brute nu se pot compara direct: schemele stau în spatele unui $ref, iar tipul e împărțit în type + format. De aceea comparația are două etape distincte.

openapi-v1.json(brut, cu $ref)

normalize()rezolvă $ref, aplatizează,type = type + format

openapi-v2.json(brut, cu $ref)

normalize()

METHOD PATH →params / body / responses

METHOD PATH →params / body / responses

compare_specs()reguli deterministe, fără model

BREAKING

WARNING

SAFE

Principiul central: request-urile pot deveni doar mai permisive, response-urile pot deveni doar mai bogate. Direcția opusă e breaking — un client trimite cereri și citește răspunsuri, nu invers.
4. Regulile de compatibilitate
Codificate în app/comparator.py și documentate textual în knowledge/*.md — identificatorii apar identic în ambele, ceea ce permite tool-ului search_documents să lege un verdict de justificarea lui.

Regulă	Severitate	De ce
ENDPOINT_REMOVED	breaking	404 pentru orice client existent
PARAM_NOW_REQUIRED	breaking	400 pentru clienții care nu-l trimiteau
PARAM_TYPE_CHANGED	breaking	deserializarea eșuează
PARAM_ENUM_VALUE_REMOVED	breaking	valoare validă anterior, respinsă acum
REQUEST_FIELD_REMOVED	breaking	intenția clientului e ignorată silențios
RESPONSE_FIELD_REMOVED	breaking	clientul citește null, eșuează mai târziu
RESPONSE_STATUS_REMOVED	breaking	ramurile de status nu se mai potrivesc
RESPONSE_ENUM_VALUE_ADDED	warning	switch-urile exhaustive pică la runtime
ENDPOINT_ADDED	safe	nimeni nu-l apelează încă
PARAM_NOW_OPTIONAL	safe	constrângere relaxată
RESPONSE_FIELD_ADDED	safe	clienții toleranți îl ignoră
5. Sursa datelor de test — mock-ul Java
api-mock/ există ca să producă date realiste: schimbări plantate direct în cod Java, nu specificații scrise de mână. springdoc-openapi generează spec-ul reflectând peste controllere, deci /v3/api-docs reflectă mereu codul curent.

Versiune	Ce s-a schimbat în Java	Rezultat
v1	baseline	—
v2	endpoint șters, parametru devenit required, câmp eliminat, Double→BigDecimal, enum micșorat	17 breaking
v3	endpoint nou, parametru opțional nou, enum restaurat	0 breaking 5 warning
Endpoint	Metodă
/api/products	GET, POST
/api/products/search	GET
/api/products/{id}	GET, PUT
/api/products/{id}/similar	GET
/api/products/health	GET
6. Structura repo-ului
.
├── api-diff-python/        # agentul AI — singura parte deployată
│   ├── app/
│   │   ├── agent.py         # definește root_agent (ADK) + 5 tool-uri
│   │   ├── tools.py         # list_api_versions, compare_api_versions, ...
│   │   ├── comparator.py    # regulile deterministe BREAKING/WARNING/SAFE
│   │   ├── normalizer.py    # rezolvă $ref, aplatizează schemele
│   │   ├── knowledge.py     # LocalKnowledgeProvider / CloudKnowledgeProvider
│   │   ├── prompts.py       # system prompt — "Python decide, Gemini explică"
│   │   └── config.py        # .env → Config (local vs. cloud)
│   ├── knowledge/            # *.json specs + *.md reguli
│   ├── scripts/               # upload_knowledge, verify_local_setup
│   ├── tests/                 # câte un assert per regulă plantată
│   ├── Dockerfile
│   └── main.py               # demo local, fără Gemini
├── api-mock/               # Spring Boot — generează spec-urile de test
│   └── src/main/java/org/example/apimock/
│       ├── controller/ProductController.java
│       ├── service/ProductService.java
│       └── entity/{Product,Category}.java
├── specs/                  # export-uri brute /v3/api-docs
├── terraform/               # infra ca și cod
└── .github/workflows/ci.yml  # 4 job-uri: python · java · terraform · docker
7. Infrastructură & deploy
terraform/main.tf descrie declarativ ce altfel ar fi o secvență de comenzi gcloud greu de reprodus.

Resursă	Scop
google_storage_bucket	bucket-ul de cunoștințe (<project>-api-diff-kb)
google_storage_bucket_object	încarcă fiecare fișier din knowledge/ via fileset()
google_service_account	identitatea de rulare api-diff-runner
google_storage_bucket_iam_member	acces read-only la bucket
google_project_iam_member	permisiune de a apela Gemini (roles/aiplatform.user)
google_cloud_run_v2_service	serviciul, imaginea și variabilele de mediu
8. Workflow — trei viteze independente
Motivul practic pentru care baza de cunoștințe stă în afara imaginii Docker: fiecare tip de schimbare are propriul cost.

Ce se schimbă	Unde trăiește	Cum se actualizează	Durată
Specificații, reguli	Cloud Storage	python scripts/upload_knowledge.py	secunde
Configurație	Cloud Run env vars	gcloud run services update	~30 s
Cod Python	imaginea container	build → push → deploy	~3 min
Diagramă generată din codul sursă existent (Python, Java, Terraform, CI) — nu adaugă nimic ce nu e deja în repo.
