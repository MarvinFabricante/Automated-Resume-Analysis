import re

# ─── Comprehensive Skills Knowledge Base ─────────────────────────────────────
# All values UPPER-CASE for O(1) lookup.

_PROGRAMMING_LANGUAGES = {
    "PYTHON", "JAVASCRIPT", "TYPESCRIPT", "JAVA", "C", "C++", "C#", "RUBY", "PHP",
    "SWIFT", "KOTLIN", "GO", "GOLANG", "RUST", "R", "SCALA", "PERL", "LUA",
    "OBJECTIVE-C", "DART", "ELIXIR", "HASKELL", "CLOJURE", "F#", "MATLAB",
    "VISUAL BASIC", "VB.NET", "ASSEMBLY", "GROOVY", "SHELL", "POWERSHELL",
    "COFFEESCRIPT", "SOLIDITY", "COBOL", "FORTRAN", "JULIA", "ZIG",
}

_WEB_FRAMEWORKS = {
    "REACT", "REACT.JS", "REACTJS", "ANGULAR", "ANGULARJS", "VUE", "VUE.JS", "VUEJS",
    "NEXT.JS", "NEXTJS", "NUXT.JS", "NUXTJS", "SVELTE", "SVELTEKIT",
    "NODE.JS", "NODEJS", "EXPRESS", "EXPRESS.JS", "EXPRESSJS", "FASTAPI", "FLASK",
    "DJANGO", "SPRING", "SPRING BOOT", "LARAVEL", "RAILS", "RUBY ON RAILS",
    "ASP.NET", "ASP.NET CORE", ".NET", ".NET CORE", "BLAZOR",
    "NEST.JS", "NESTJS", "REMIX", "GATSBY", "EMBER", "EMBER.JS",
    "BACKBONE.JS", "METEOR", "HAPI", "KOA", "FASTIFY",
    "BOOTSTRAP", "TAILWINDCSS", "TAILWIND CSS", "TAILWIND", "MATERIAL UI", "MUI",
    "CHAKRA UI", "ANT DESIGN", "SHADCN", "JQUERY", "THREE.JS", "D3.JS",
}

_DATA_ML = {
    "MACHINE LEARNING", "DEEP LEARNING", "ARTIFICIAL INTELLIGENCE", "AI", "ML",
    "NATURAL LANGUAGE PROCESSING", "NLP", "COMPUTER VISION",
    "DATA SCIENCE", "DATA ANALYSIS", "DATA ANALYTICS", "DATA ENGINEERING",
    "DATA VISUALIZATION", "DATA MINING", "DATA WAREHOUSING", "DATA MODELING",
    "BIG DATA", "ETL", "ELT",
    "PANDAS", "NUMPY", "SCIPY", "MATPLOTLIB", "SEABORN", "PLOTLY",
    "TENSORFLOW", "PYTORCH", "KERAS", "SCIKIT-LEARN", "SKLEARN",
    "OPENCV", "SPACY", "NLTK", "HUGGING FACE", "TRANSFORMERS",
    "XGBOOST", "LIGHTGBM", "CATBOOST", "RANDOM FOREST",
    "POWER BI", "TABLEAU", "LOOKER", "QLIK", "METABASE",
    "APACHE SPARK", "SPARK", "HADOOP", "HIVE", "KAFKA", "AIRFLOW",
    "DATABRICKS", "SNOWFLAKE", "DATALAKE", "REDSHIFT",
    "JUPYTER", "JUPYTER NOTEBOOK", "GOOGLE COLAB",
    "STATISTICS", "STATISTICAL ANALYSIS", "REGRESSION", "CLASSIFICATION",
    "CLUSTERING", "NEURAL NETWORKS", "CNN", "RNN", "LSTM", "GAN",
    "REINFORCEMENT LEARNING", "GENERATIVE AI", "LLM", "GPT", "PROMPT ENGINEERING",
}

_DATABASES = {
    "SQL", "MYSQL", "POSTGRESQL", "POSTGRES", "SQLITE", "ORACLE", "ORACLE DB",
    "SQL SERVER", "MSSQL", "MS SQL", "MARIADB",
    "MONGODB", "MONGO", "DYNAMODB", "CASSANDRA", "COUCHDB", "COUCHBASE",
    "REDIS", "MEMCACHED", "ELASTICSEARCH", "ELASTIC", "OPENSEARCH",
    "NEO4J", "GRAPHQL", "PRISMA", "SEQUELIZE", "SQLALCHEMY",
    "SUPABASE", "FIREBASE", "FIRESTORE", "REALM",
    "INFLUXDB", "TIMESCALEDB", "COCKROACHDB",
}

_DEVOPS_CLOUD = {
    "AWS", "AMAZON WEB SERVICES", "AZURE", "MICROSOFT AZURE", "GCP",
    "GOOGLE CLOUD", "GOOGLE CLOUD PLATFORM",
    "DOCKER", "KUBERNETES", "K8S", "HELM", "TERRAFORM", "ANSIBLE", "PUPPET", "CHEF",
    "CI/CD", "CICD", "JENKINS", "GITHUB ACTIONS", "GITLAB CI", "CIRCLECI",
    "BITBUCKET PIPELINES", "AZURE DEVOPS", "ARGOCD",
    "NGINX", "APACHE", "CADDY", "TRAEFIK",
    "LINUX", "UBUNTU", "CENTOS", "DEBIAN", "RED HAT", "RHEL",
    "WINDOWS SERVER", "MACOS",
    "BASH", "SHELL SCRIPTING", "POWERSHELL",
    "PROMETHEUS", "GRAFANA", "DATADOG", "NEW RELIC", "SPLUNK", "ELK STACK",
    "CLOUDFLARE", "VERCEL", "NETLIFY", "HEROKU", "DIGITALOCEAN", "LINODE",
    "S3", "EC2", "LAMBDA", "ECS", "EKS", "FARGATE", "CLOUDFORMATION",
    "SERVERLESS", "MICROSERVICES", "SERVICE MESH", "ISTIO",
    "VAGRANT", "PACKER", "CONSUL",
}

_TOOLS_VERSION_CONTROL = {
    "GIT", "GITHUB", "GITLAB", "BITBUCKET", "SVN", "SUBVERSION", "MERCURIAL",
    "JIRA", "CONFLUENCE", "TRELLO", "ASANA", "MONDAY.COM", "NOTION", "CLICKUP",
    "SLACK", "TEAMS", "MICROSOFT TEAMS",
    "POSTMAN", "INSOMNIA", "SWAGGER", "OPENAPI",
    "VS CODE", "VISUAL STUDIO CODE", "VISUAL STUDIO", "INTELLIJ", "PYCHARM",
    "ECLIPSE", "XCODE", "ANDROID STUDIO", "WEBSTORM", "RIDER",
    "FIGMA", "SKETCH", "ADOBE XD", "INVISION", "ZEPLIN",
    "PHOTOSHOP", "ILLUSTRATOR", "AFTER EFFECTS", "PREMIERE PRO",
    "ADOBE CREATIVE SUITE", "ADOBE CREATIVE CLOUD", "CANVA", "LIGHTROOM",
    "BLENDER", "UNITY", "UNREAL ENGINE",
}

_TESTING_QA = {
    "UNIT TESTING", "INTEGRATION TESTING", "E2E TESTING", "END-TO-END TESTING",
    "TDD", "TEST-DRIVEN DEVELOPMENT", "BDD", "BEHAVIOR-DRIVEN DEVELOPMENT",
    "JEST", "MOCHA", "CHAI", "CYPRESS", "PLAYWRIGHT", "SELENIUM", "PUPPETEER",
    "PYTEST", "UNITTEST", "ROBOT FRAMEWORK",
    "JUNIT", "TESTNG", "MOCKITO",
    "APPIUM", "DETOX", "ENZYME", "REACT TESTING LIBRARY",
    "LOAD TESTING", "PERFORMANCE TESTING", "JMETER", "GATLING", "K6",
    "QA", "QUALITY ASSURANCE", "SOFTWARE TESTING", "MANUAL TESTING",
    "AUTOMATION TESTING", "TEST AUTOMATION",
}

_MOBILE = {
    "IOS", "ANDROID", "REACT NATIVE", "FLUTTER", "XAMARIN", "IONIC",
    "SWIFTUI", "JETPACK COMPOSE", "KOTLIN MULTIPLATFORM", "MAUI",
    "MOBILE DEVELOPMENT", "MOBILE APP DEVELOPMENT",
    "PROGRESSIVE WEB APP", "PWA", "EXPO",
}

_SECURITY = {
    "CYBERSECURITY", "CYBER SECURITY", "INFORMATION SECURITY", "INFOSEC",
    "NETWORK SECURITY", "APPLICATION SECURITY", "CLOUD SECURITY",
    "PENETRATION TESTING", "PEN TESTING", "ETHICAL HACKING",
    "VULNERABILITY ASSESSMENT", "SIEM", "SOC",
    "OWASP", "SSL/TLS", "ENCRYPTION", "OAUTH", "JWT", "SSO",
    "IDENTITY AND ACCESS MANAGEMENT", "IAM", "ZERO TRUST",
    "FIREWALL", "IDS", "IPS", "WAF", "VPN",
    "COMPLIANCE", "GDPR", "HIPAA", "SOC 2", "ISO 27001", "PCI DSS",
}

_SOFT_SKILLS = {
    "AGILE", "SCRUM", "KANBAN", "LEAN", "SAFe",
    "PROJECT MANAGEMENT", "PROGRAM MANAGEMENT", "PRODUCT MANAGEMENT",
    "LEADERSHIP", "TEAM LEADERSHIP", "TEAM MANAGEMENT", "PEOPLE MANAGEMENT",
    "COMMUNICATION", "PRESENTATION", "PUBLIC SPEAKING",
    "PROBLEM SOLVING", "CRITICAL THINKING", "ANALYTICAL THINKING",
    "DECISION MAKING", "STRATEGIC PLANNING", "STRATEGIC THINKING",
    "TIME MANAGEMENT", "ORGANIZATIONAL SKILLS",
    "COLLABORATION", "TEAMWORK", "CROSS-FUNCTIONAL",
    "MENTORING", "COACHING", "TRAINING",
    "STAKEHOLDER MANAGEMENT", "CLIENT RELATIONS", "CLIENT MANAGEMENT",
    "NEGOTIATION", "CONFLICT RESOLUTION",
}

_BUSINESS_DOMAIN = {
    "CUSTOMER SERVICE", "SALES", "MARKETING", "DIGITAL MARKETING",
    "SOCIAL MEDIA MARKETING", "EMAIL MARKETING", "CONTENT MARKETING",
    "SEO", "SEM", "PPC", "GOOGLE ADS", "FACEBOOK ADS", "GOOGLE ANALYTICS",
    "CONTENT CREATION", "COPYWRITING", "TECHNICAL WRITING", "DOCUMENTATION",
    "UI/UX", "UX DESIGN", "UI DESIGN", "USER EXPERIENCE", "USER INTERFACE",
    "PRODUCT DESIGN", "INTERACTION DESIGN", "WIREFRAMING", "PROTOTYPING",
    "MICROSOFT OFFICE", "MICROSOFT 365", "EXCEL", "WORD", "POWERPOINT",
    "GOOGLE WORKSPACE", "GOOGLE SHEETS", "GOOGLE DOCS",
    "SAP", "SALESFORCE", "HUBSPOT", "ZOHO",
    "ERP", "CRM", "SUPPLY CHAIN MANAGEMENT", "LOGISTICS",
    "ACCOUNTING", "BOOKKEEPING", "QUICKBOOKS", "XERO",
    "FINANCIAL ANALYSIS", "FINANCIAL MODELING", "BUDGETING", "FORECASTING",
    "BUSINESS ANALYSIS", "BUSINESS INTELLIGENCE", "BI",
    "REQUIREMENTS GATHERING", "PROCESS IMPROVEMENT", "SIX SIGMA",
}

_API_MISC = {
    "REST", "REST API", "RESTFUL", "RESTFUL API",
    "GRAPHQL", "GRPC", "SOAP", "WEBSOCKET", "WEBSOCKETS",
    "API DEVELOPMENT", "API DESIGN", "API INTEGRATION",
    "OAUTH 2.0", "SAML",
    "HTML", "HTML5", "CSS", "CSS3", "SASS", "SCSS", "LESS",
    "WEBPACK", "VITE", "PARCEL", "ROLLUP", "ESBUILD", "BABEL",
    "NPM", "YARN", "PNPM", "PIP", "POETRY", "CONDA",
    "JSON", "XML", "YAML", "TOML", "CSV",
    "RESPONSIVE DESIGN", "RESPONSIVE WEB DESIGN", "ACCESSIBILITY", "WCAG",
    "SEO OPTIMIZATION", "WEB PERFORMANCE", "CORE WEB VITALS",
    "BLOCKCHAIN", "WEB3", "SMART CONTRACTS", "DEFI", "NFT",
    "IOT", "INTERNET OF THINGS", "EMBEDDED SYSTEMS", "ARDUINO", "RASPBERRY PI",
    "RPA", "ROBOTIC PROCESS AUTOMATION", "UIPATH", "AUTOMATION ANYWHERE",
    "SYSTEM ADMINISTRATION", "SYSADMIN", "ACTIVE DIRECTORY",
    "VIRTUALIZATION", "VMWARE", "HYPER-V",
}

# Union of all categories
COMMON_SKILLS: set[str] = (
    _PROGRAMMING_LANGUAGES | _WEB_FRAMEWORKS | _DATA_ML | _DATABASES |
    _DEVOPS_CLOUD | _TOOLS_VERSION_CONTROL | _TESTING_QA | _MOBILE |
    _SECURITY | _SOFT_SKILLS | _BUSINESS_DOMAIN | _API_MISC
)

# ─── Synonym Mapping ─────────────────────────────────────────────────────────
# Maps alternate forms to a canonical skill name for deduplication
_SKILL_SYNONYMS = {
    "REACTJS": "REACT", "REACT.JS": "REACT",
    "VUEJS": "VUE", "VUE.JS": "VUE",
    "ANGULARJS": "ANGULAR",
    "NEXTJS": "NEXT.JS", "NUXTJS": "NUXT.JS",
    "NODEJS": "NODE.JS", "EXPRESSJS": "EXPRESS",
    "NESTJS": "NEST.JS",
    "GOLANG": "GO",
    "POSTGRES": "POSTGRESQL",
    "MONGO": "MONGODB",
    "ELASTIC": "ELASTICSEARCH",
    "K8S": "KUBERNETES",
    "SKLEARN": "SCIKIT-LEARN",
    "CICD": "CI/CD",
    "TAILWIND": "TAILWINDCSS", "TAILWIND CSS": "TAILWINDCSS",
    "AMAZON WEB SERVICES": "AWS",
    "MICROSOFT AZURE": "AZURE",
    "GOOGLE CLOUD": "GCP", "GOOGLE CLOUD PLATFORM": "GCP",
    "MSSQL": "SQL SERVER", "MS SQL": "SQL SERVER",
}

# ─── Casing Overrides ────────────────────────────────────────────────────────

_UPPER_CASE_SKILLS = {
    "html", "html5", "css", "css3", "php", "sql", "mysql", "seo", "sem",
    "ui/ux", "aws", "gcp", "api", "rest", "rest api", "restful", "grpc",
    "graphql", "nosql", "json", "xml", "yaml", "csv", "ci/cd", "devops",
    "qa", "tdd", "bdd", "etl", "elt", "bi", "ai", "ml", "nlp", "cnn",
    "rnn", "lstm", "gan", "llm", "gpt", "jwt", "sso", "oauth", "ssl/tls",
    "iam", "gdpr", "hipaa", "pci dss", "iso 27001", "soc 2", "rpa",
    "iot", "nft", "erp", "crm", "pwa", "saas", "paas", "iaas",
    "sass", "scss", "less", "npm", "yarn", "pnpm", "pip",
    "k8s", "ec2", "s3", "eks", "ecs",
}

_TITLE_CASE_OVERRIDES = {
    "node.js": "Node.js", "react.js": "React.js", "vue.js": "Vue.js",
    "next.js": "Next.js", "nuxt.js": "Nuxt.js", "express.js": "Express.js",
    "nest.js": "Nest.js", "angular.js": "Angular.js", "ember.js": "Ember.js",
    "backbone.js": "Backbone.js", "three.js": "Three.js",
    "d3.js": "D3.js", "p5.js": "p5.js",
    "asp.net": "ASP.NET", "asp.net core": "ASP.NET Core",
    ".net": ".NET", ".net core": ".NET Core",
    "vb.net": "VB.NET", "f#": "F#", "c#": "C#", "c++": "C++",
    "objective-c": "Objective-C",
    "scikit-learn": "Scikit-learn", "xgboost": "XGBoost",
    "lightgbm": "LightGBM", "catboost": "CatBoost",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch",
    "opencv": "OpenCV", "fastapi": "FastAPI",
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mongodb": "MongoDB", "dynamodb": "DynamoDB",
    "couchdb": "CouchDB", "couchbase": "Couchbase",
    "neo4j": "Neo4j", "influxdb": "InfluxDB",
    "cockroachdb": "CockroachDB", "timescaledb": "TimescaleDB",
    "elasticsearch": "Elasticsearch", "opensearch": "OpenSearch",
    "supabase": "Supabase", "firebase": "Firebase",
    "github": "GitHub", "gitlab": "GitLab", "bitbucket": "Bitbucket",
    "kubernetes": "Kubernetes", "docker": "Docker",
    "terraform": "Terraform", "ansible": "Ansible",
    "jenkins": "Jenkins", "argocd": "ArgoCD",
    "cloudflare": "Cloudflare", "vercel": "Vercel", "netlify": "Netlify",
    "heroku": "Heroku", "digitalocean": "DigitalOcean",
    "datadog": "Datadog", "grafana": "Grafana", "prometheus": "Prometheus",
    "splunk": "Splunk", "jira": "Jira", "confluence": "Confluence",
    "salesforce": "Salesforce", "hubspot": "HubSpot",
    "quickbooks": "QuickBooks",
    "typescript": "TypeScript", "javascript": "JavaScript",
    "powershell": "PowerShell",
    "android": "Android", "ios": "iOS",
    "flutter": "Flutter", "react native": "React Native",
    "swiftui": "SwiftUI", "jetpack compose": "Jetpack Compose",
    "tailwindcss": "TailwindCSS", "tailwind css": "TailwindCSS",
    "bootstrap": "Bootstrap", "material ui": "Material UI",
    "chakra ui": "Chakra UI",
    "webpack": "Webpack", "vite": "Vite", "babel": "Babel",
    "selenium": "Selenium", "cypress": "Cypress", "playwright": "Playwright",
    "pytest": "pytest", "jest": "Jest",
    "figma": "Figma", "photoshop": "Photoshop", "illustrator": "Illustrator",
    "canva": "Canva", "blender": "Blender",
    "power bi": "Power BI", "tableau": "Tableau", "looker": "Looker",
    "snowflake": "Snowflake", "databricks": "Databricks",
    "apache spark": "Apache Spark", "spark": "Spark",
    "hadoop": "Hadoop", "kafka": "Kafka", "airflow": "Airflow",
    "redis": "Redis", "memcached": "Memcached",
    "prisma": "Prisma", "sequelize": "Sequelize", "sqlalchemy": "SQLAlchemy",
    "spring boot": "Spring Boot", "spring": "Spring",
    "django": "Django", "flask": "Flask", "laravel": "Laravel",
    "ruby on rails": "Ruby on Rails",
    "svelte": "Svelte", "sveltekit": "SvelteKit",
    "remix": "Remix", "gatsby": "Gatsby",
    "uipath": "UiPath",
}


def _format_skill(skill: str) -> str:
    """Apply proper casing to a skill string."""
    lower = skill.strip().lower()
    if not lower:
        return ""
    if lower in _TITLE_CASE_OVERRIDES:
        return _TITLE_CASE_OVERRIDES[lower]
    if lower in _UPPER_CASE_SKILLS:
        return skill.strip().upper()
    return skill.strip().title()


# ─── Section header keywords ─────────────────────────────────────────────────

_SKILL_HEADERS = [
    "SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES", "EXPERTISE",
    "TECHNOLOGIES", "TOOLS", "KEY SKILLS", "PROFICIENCIES",
    "COMPETENCIES", "TECH STACK", "TECHNICAL COMPETENCIES",
    "AREAS OF EXPERTISE", "PROFESSIONAL SKILLS", "SKILL SET",
    "TOOLS & TECHNOLOGIES", "TOOLS AND TECHNOLOGIES",
    "PROGRAMMING LANGUAGES", "FRAMEWORKS", "SOFTWARE",
    "TECHNICAL PROFICIENCY", "QUALIFICATIONS SUMMARY",
]

_STOP_HEADERS = [
    "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE",
    "EDUCATION", "CERTIFICATIONS", "PROJECTS", "WORK HISTORY",
    "EMPLOYMENT", "REFERENCES", "ACHIEVEMENTS", "AFFILIATIONS",
    "BACKGROUND", "PUBLICATIONS", "AWARDS", "INTERESTS",
    "OBJECTIVE", "SUMMARY", "ABOUT ME", "PROFILE",
    "VOLUNTEER", "HOBBIES", "LANGUAGES", "PERSONAL INFORMATION",
    "TRAINING", "SEMINARS", "ACTIVITIES",
]

# ─── Noise words that should never be extracted as skills ─────────────────────

_NOISE_WORDS = {
    'and', 'or', 'the', 'for', 'with', 'in', 'of', 'to', 'a', 'an',
    'is', 'at', 'on', 'by', 'etc', 'i', 'ii', 'iii', 'iv', 'v',
    'years', 'year', 'experience', 'experienced', 'proficient',
    'strong', 'excellent', 'good', 'knowledge', 'understanding',
    'familiar', 'basic', 'advanced', 'intermediate', 'expert',
    'level', 'including', 'using', 'working', 'used',
    'responsible', 'developed', 'managed', 'implemented', 'created',
    'designed', 'built', 'led', 'maintained', 'improved',
    'various', 'multiple', 'several', 'other', 'related',
    'tools', 'technologies', 'skills', 'ability', 'abilities',
    'proficiency', 'competency', 'expertise',
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
    'present', 'current', 'ongoing',
    'city', 'street', 'province', 'philippines', 'manila',
    'resume', 'cv', 'curriculum', 'vitae', 'page',
}


def _is_section_header(line: str, keywords: list[str]) -> bool:
    """Check if a line is a section header matching any of the keywords."""
    clean = line.strip().upper()
    if not clean:
        return False
    if len(clean.split()) >= 6:
        return False
    for kw in keywords:
        if clean == kw or clean.startswith(kw + ":") or clean.startswith(kw + " :"):
            return True
        stripped = clean.strip("-=_*#•► ").strip()
        if stripped == kw or stripped.startswith(kw + ":"):
            return True
    return False


def _split_skill_items(raw_text: str) -> list[str]:
    """Split a raw skills string into individual skill tokens."""
    text = raw_text
    for d in ['|', '•', '●', '◦', '▪', '►', '★', '✓', '✔', ';']:
        text = text.replace(d, ',')

    # Replace standalone hyphens/dashes used as list delimiters
    text = re.sub(r'(?<!\w)\s*[-–—]\s+', ', ', text)

    items = []
    for chunk in text.split(','):
        cleaned = chunk.strip().strip('*').strip()
        if cleaned and 1 < len(cleaned) < 60:
            items.append(cleaned)
    return items


def _get_canonical_key(skill_upper: str) -> str:
    """Get the canonical key for deduplication using synonym mapping."""
    return _SKILL_SYNONYMS.get(skill_upper, skill_upper)


def _extract_contextual_skills(text: str) -> list[str]:
    """
    Extract skills mentioned in context (experience descriptions, project details).
    Looks for patterns like "using Python and React", "proficient in Docker",
    "experience with AWS", "built with Next.js", etc.
    Uses expanded verb/preposition patterns to maximize recall without an LLM.
    """
    contextual_patterns = [
        r'(?:using|with|in|including|such\s+as|like|utilized|leveraging|'
        r'proficient\s+in|experienced?\s+(?:in|with)|familiar\s+with|'
        r'knowledge\s+of|expertise\s+in|skilled\s+in|'
        r'built\s+(?:with|using|in)|developed\s+(?:with|using|in)|'
        r'implemented\s+(?:with|using|in)|worked\s+(?:with|on)|'
        r'deployed\s+(?:on|to|with|using)|migrated\s+to|'
        r'integrated\s+(?:with|into)|configured\s+|'
        r'managed\s+|administered\s+|maintained\s+|'
        r'wrote\s+(?:in|using)|coded\s+(?:in|using)|'
        r'automated\s+(?:with|using)|orchestrated\s+(?:with|using)|'
        r'tested\s+(?:with|using)|monitored\s+(?:with|using)|'
        r'designed\s+(?:with|using|in)|created\s+(?:with|using|in)|'
        r'architected\s+(?:with|using)|optimized\s+(?:with|using))\s+'
        r'([^.!?\n]{3,120})',
    ]

    found_skills = []
    for pattern in contextual_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            fragment = m.group(1)
            # Split the fragment and check each token against the KB
            tokens = re.split(r'[,;|]|\band\b|\bor\b', fragment)
            for token in tokens:
                token_clean = token.strip().upper()
                token_clean = re.sub(r'^[^A-Z0-9]+|[^A-Z0-9]+$', '', token_clean)
                if token_clean in COMMON_SKILLS:
                    found_skills.append(token_clean)

    return found_skills


def _extract_inline_category_skills(text: str) -> list[str]:
    """
    Pass 4: Extract skills from inline "Category: skill1, skill2" patterns
    commonly found in resumes, e.g.:
      - Programming Languages: Python, Java, C++
      - Databases: MySQL, PostgreSQL, MongoDB
      - Tools & Technologies: Docker, Kubernetes, AWS
    """
    category_pattern = re.compile(
        r'^[\s•\-►▪*]*'
        r'(?:Programming\s+Languages?|Languages?|Frameworks?|Libraries|'
        r'Databases?|Tools?|Technologies|Platforms?|Cloud|DevOps|'
        r'Operating\s+Systems?|Software|IDEs?|Version\s+Control|'
        r'Frontend|Backend|Full[\s\-]?Stack|Mobile|Testing|'
        r'Data(?:bases?|\s+Tools)?|Other|Miscellaneous|Additional|'
        r'(?:Tools?\s*(?:&|and)\s*(?:Technologies|Frameworks?)?))'
        r'\s*[:]\s*(.+)',
        re.IGNORECASE | re.MULTILINE
    )

    found_skills = []
    for m in category_pattern.finditer(text):
        value = m.group(1).strip()
        tokens = re.split(r'[,;|•]', value)
        for token in tokens:
            token_clean = token.strip().upper()
            token_clean = re.sub(r'^[^A-Z0-9]+|[^A-Z0-9]+$', '', token_clean)
            if token_clean in COMMON_SKILLS:
                found_skills.append(token_clean)

    return found_skills


def extract_skills(text: str) -> str:
    """
    Extracts skills from resume text using a four-pass approach:
      1. Section-based extraction: find the skills section and parse its content.
      2. Contextual extraction: find skills mentioned in experience/project descriptions.
      3. Full-document KB scan: match known skills from the knowledge base.
      4. Inline category extraction: parse "Category: skill1, skill2" patterns.

    No LLM/AI is used. Returns a pipe-separated string of identified skills
    (deduplicated, properly cased).
    """
    lines = text.split('\n')

    # ── Pass 1: Section-based extraction ──────────────────────────────────────
    section_skills: list[str] = []
    found_section = False
    section_lines: list[str] = []

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue

        if _is_section_header(clean_line, _SKILL_HEADERS):
            if found_section and section_lines:
                section_skills.extend(_split_skill_items(" ".join(section_lines)))
                section_lines = []
            found_section = True
            colon_idx = clean_line.find(':')
            if colon_idx >= 0:
                after_colon = clean_line[colon_idx + 1:].strip()
                if after_colon:
                    section_lines.append(after_colon)
            continue

        if found_section:
            if _is_section_header(clean_line, _STOP_HEADERS):
                break
            section_lines.append(clean_line)

    if section_lines:
        section_skills.extend(_split_skill_items(" ".join(section_lines)))

    # ── Pass 2: Contextual extraction from experience/project text ────────────
    contextual_skills = _extract_contextual_skills(text)

    # ── Pass 3: Knowledge-base scan across entire document ────────────────────
    kb_skills: list[str] = []
    text_upper = text.upper()

    sorted_skills = sorted(COMMON_SKILLS, key=len, reverse=True)
    matched_positions: list[tuple[int, int]] = []

    for skill in sorted_skills:
        pattern = r'\b' + re.escape(skill) + r'\b'
        for m in re.finditer(pattern, text_upper):
            start, end = m.start(), m.end()
            overlaps = any(
                not (end <= es or start >= ee)
                for es, ee in matched_positions
            )
            if not overlaps:
                matched_positions.append((start, end))
                kb_skills.append(skill)
                break

    # ── Pass 4: Inline category:value patterns ────────────────────────────────
    inline_skills = _extract_inline_category_skills(text)

    # ── Merge & deduplicate with synonym-aware dedup ──────────────────────────
    seen_canonical: set[str] = set()
    unique_skills: list[str] = []

    def _add_skill(raw: str):
        formatted = _format_skill(raw)
        if not formatted:
            return
        key = formatted.lower().strip()
        if key in _NOISE_WORDS or len(key) < 2:
            return
        # Canonical dedup
        canonical = _get_canonical_key(formatted.upper().strip())
        if canonical not in seen_canonical:
            seen_canonical.add(canonical)
            unique_skills.append(formatted)

    # Priority: section > contextual > inline > KB
    for s in section_skills:
        _add_skill(s)
    for s in contextual_skills:
        _add_skill(s)
    for s in inline_skills:
        _add_skill(s)
    for s in kb_skills:
        _add_skill(s)

    return " | ".join(unique_skills[:50]) if unique_skills else ""
