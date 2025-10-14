from rdflib import Graph, Namespace, RDF, RDFS, Literal
from difflib import SequenceMatcher

ontology_file = "bg3_no_age_updated.rdf"
BG3 = Namespace("http://www.semanticweb.org/chenqing/ontologies/2025/9/bg3#")

pref_ru = {
    "beginner": "новых",
    "intermediate": "опытных",
    "advanced": "профессиональных",
}

token_map = {
    "новичок": "beginner",
    "начинающий": "beginner",
    "опытный": "advanced",
    "продвинутый": "advanced",
    "средний": "intermediate",
    "нормальный": "intermediate",
}

def normalize_tokens_fuzzy(tokens):
    norm_tokens = []
    for tok in tokens:
        tok_lower = tok.lower()
        # ищем самое похожее слово в token_map
        best_match = tok_lower
        best_ratio = 0
        for key, val in token_map.items():
            ratio = SequenceMatcher(None, tok_lower, key).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                if ratio >= 0.5:
                    best_match = val
        norm_tokens.append(best_match)
    return norm_tokens

def fuzzy_match(token, text, threshold=0.6):
    if not token or not text:
        return False
    return SequenceMatcher(None, token, text.lower()).ratio() >= threshold

def find_person():
    user_input = input("Опиши себя (пример: 'Привет, я новичок, люблю играть на роли поддержка, танк')\nДоступные роли: дамагер, контроль, поддержка, танк, хилер\n> ")
    tokens = normalize_tokens_fuzzy(user_input.replace(",", " ").split())

    pref_tokens = [t for t in tokens if t in ["beginner","easy","intermediate","advanced"]]
    role_tokens = [t for t in tokens if t not in pref_tokens]

    g = Graph()
    g.parse(ontology_file)

    query = """
    PREFIX bg3: <http://www.semanticweb.org/chenqing/ontologies/2025/9/bg3#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?char ?charLabel ?roleLabel ?classLabel ?pref ?hp
    WHERE {
        ?char rdf:type bg3:Character .
        OPTIONAL { ?char rdfs:label ?charLabel. }
        OPTIONAL { 
            ?char bg3:hasRole ?role .
            ?role rdfs:label ?roleLabel.
        }
        OPTIONAL {
            ?char bg3:hasClass ?class .
            ?class rdfs:label ?classLabel.
            ?class bg3:classPreference ?pref .
            ?class bg3:maxHP ?hp .
        }
    }
    """

    results = g.query(query)

    perfect_match = []
    role_only = []
    pref_only = []

    for row in results:
        name = str(row.charLabel or row.char)
        role = str(row.roleLabel or "").lower()
        cls = str(row.classLabel or "").lower()
        pref = str(row.pref or "").lower()
        hp = row.hp.toPython() if isinstance(row.hp, Literal) else None

        matched_role = any(fuzzy_match(tok, role) for tok in role_tokens)
        matched_pref = any(fuzzy_match(tok, pref) for tok in pref_tokens)

        if matched_role and matched_pref:
            perfect_match.append((name, cls, role, hp, pref))
        elif matched_role:
            role_only.append((name, cls, role, hp, pref))
        elif matched_pref:
            pref_only.append((name, cls, role, hp, pref))

    def print_chars(chars, title):
        print(f"\n{title}\n")
        for name, cls, role, hp, pref in chars:
            print(f"— {name}")
            if cls: print(f"   • Класс: {cls}")
            if role: print(f"   • Роль: {role}")
            if pref: print(f"   • Подходит для: {pref_ru.get(pref, pref)} игроков")
            if hp: print(f"   • Max HP: {hp}")
            print()

    if perfect_match:
        print_chars(perfect_match, "Персонажи, где совпали и роль, и уровень:")
    if role_only:
        print_chars(role_only, "Совпала только роль:")
    if pref_only:
        print_chars(pref_only, "Совпал только уровень (опыт игры):")

    if not (perfect_match or role_only or pref_only):
        print("Ничего не найдено. Попробуй другие предпочтения.")
        find_person()

find_person()
