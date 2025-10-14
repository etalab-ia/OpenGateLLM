# Advanced RAG pipeline
<p align="right">
[![](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/advanced_rag_pipeline.ipynb)
</p>



```python
import requests
import time
import base64
from typing import Optional, Dict, Any
```


```python
try:
    from IPython.display import Image, display
    JUPYTER_AVAILABLE = True
    print("📱 Jupyter environment detected - image display enabled")
except ImportError:
    JUPYTER_AVAILABLE = False
    print("📱 Standard environment - HTML image display")
```

> ```
> 📱 Jupyter environment detected - image display enabled
> ```


```python
# API Configuration
BASE_URL = "XXX"  # Replace with your API URL
API_KEY = "XXX"  # Replace with your API key

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "accept": "application/json"
}
```

# 1. DISCOVERING AVAILABLE MODELS

Let's start by looking at the models available on Albert API


```python
def get_available_models():
    """Retrieves the list of available models."""
    try:
        response = requests.get(f"{BASE_URL}/v1/models", headers=headers)
        response.raise_for_status()
        models_data = response.json()
        
        print(f"✅ {len(models_data['data'])} models found")
        
        for model in models_data['data']:
            print(f"  📱 {model.get('id', 'N/A')}")
            print(f"     Type: {model.get('type', 'N/A')}")
            
            # Handle max context which can be None
            max_context = model.get('max_context_length')
            if max_context is not None:
                print(f"     Max context: {max_context:,} tokens")
            else:
                print("     Max context: N/A")
                
            # Handle costs which can be None or missing
            costs = model.get('costs')
            if costs and isinstance(costs, dict):
                prompt_cost = costs.get('prompt_tokens', 'N/A')
                completion_cost = costs.get('completion_tokens', 'N/A')
                print(f"     Prompt cost: {prompt_cost}")
                print(f"     Completion cost: {completion_cost}")
            else:
                print("     Costs: Not available")
            print()
        
        return models_data['data']
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving models: {e}")
        return []

models = get_available_models()
```

> ```
> ✅ 5 models found
>   📱 albert-large
>      Type: image-text-to-text
>      Max context: 128,000 tokens
>      Prompt cost: 0.0
>      Completion cost: 0.0
> 
>   📱 albert-small
>      Type: text-generation
>      Max context: 64,000 tokens
>      Prompt cost: 0.0
>      Completion cost: 0.0
> 
>   📱 embeddings-small
>      Type: text-embeddings-inference
>      Max context: 8,192 tokens
>      Prompt cost: 0.0
>      Completion cost: 0.0
> 
>   📱 audio-large
>      Type: automatic-speech-recognition
>      Max context: N/A
>      Prompt cost: 0.0
>      Completion cost: 0.0
> 
>   📱 rerank-small
>      Type: text-classification
>      Max context: 8,192 tokens
>      Prompt cost: 0.0
>      Completion cost: 0.0
> ```

We select the albert-small and embeddings-small models for our example.


```python
# Search for specific desired models
preferred_chat_model = "albert-small"
preferred_embedding_model = "embeddings-small"

# Search for specific chat model
chat_model = None
for model in models:
    if model.get('id') == preferred_chat_model:
        chat_model = preferred_chat_model
        break

# Search for specific embedding model
embedding_model = None
for model in models:
    if model.get('id') == preferred_embedding_model:
        embedding_model = preferred_embedding_model
        break

# If preferred models are not found, use the first available ones as fallback
if not chat_model and models:
    chat_model = models[0].get('id', '')
    print(f"⚠️  Model '{preferred_chat_model}' not found, using first available model")

if not embedding_model and models:
    # Look for an embedding model in the list, otherwise take the first one
    for model in models:
        if 'embedding' in model.get('id', '').lower():
            embedding_model = model.get('id', '')
            break
    if not embedding_model:
        embedding_model = models[0].get('id', '')
        print(f"⚠️  Model '{preferred_embedding_model}' not found, using first available model")

print(f"🎯 Selected embedding model: {embedding_model or 'None found'}")
print(f"🎯 Selected chat model: {chat_model or 'None found'}")

if not chat_model:
    print("❌ No chat model available. Please check your API configuration.")
    print("📋 Available models:", [m.get('id') for m in models])
```

> ```
> 🎯 Selected embedding model: embeddings-small
> 🎯 Selected chat model: albert-small
> ```

# 2. DOWNLOADING AND PARSING PDF

We are going to download a PDF document that will serve as an example. To do this, we will use the Wikipedia API which will allow us to retrieve the PDF format of this page https://fr.wikipedia.org/wiki/%C3%89lectron .
We will use the parse endpoint to look at the results of our parsing tool and verify that the result is satisfactory. 


```python
def download_wikipedia_pdf() -> Optional[Dict[str, Any]]:
    """Downloads a PDF from the Wikipedia API and parses it with the API."""
    try:
        # Download PDF from Wikipedia REST API
        print("⬇️  Downloading Wikipedia PDF on electron...")
        
        # Direct URL from Wikipedia REST API to download as PDF
        wikipedia_url = "https://fr.wikipedia.org/api/rest_v1/page/pdf/Électron"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Albert-API-Demo/1.0)'
        }
        
        pdf_response = requests.get(wikipedia_url, headers=headers, timeout=30)
        pdf_response.raise_for_status()
        
        print("✅ PDF downloaded successfully!")
        print(f"📊 PDF size: {len(pdf_response.content):,} bytes")
        
        # Parsing with Albert API
        print("🔄 Parsing PDF with Albert API...")
        
        files = {
            'file': ('electron_wikipedia.pdf', pdf_response.content, 'application/pdf')
        }
        
        parse_data = {
            'output_format': 'markdown',
            'force_ocr': 'false',
            'languages': 'fr',
            'use_llm': 'false'
        }
        
        parse_response = requests.post(
            f"{BASE_URL}/v1/parse",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files=files,
            data=parse_data
        )
        parse_response.raise_for_status()
        
        parsed_data = parse_response.json()
        print("✅ PDF parsed successfully!")
        
        # Display content preview
        if parsed_data.get('data') and len(parsed_data['data']) > 0:
            content = parsed_data['data'][0]['content']
            print(f"📝 Content preview ({len(content)} characters):")
            print(content[:300] + "..." if len(content) > 300 else content)
        
        return parsed_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during download/parsing: {e}")
        print("🔄 Attempting alternative solution...")
        
        # Fallback solution: use test content on electron
        try:
            print("📄 Using alternative test document...")
            test_content = """
# The Electron

The electron is a stable elementary particle from the lepton family. 
It carries a negative elementary electric charge and has a rest mass 
of approximately 9.109 × 10⁻³¹ kg. The electron plays a fundamental role in chemistry, 
as it participates in chemical bonds.

## Main properties
- Charge: -1.602 × 10⁻¹⁹ coulombs
- Mass: 9.109 × 10⁻³¹ kg
- Spin: 1/2

## Discovery
The electron was discovered by J.J. Thomson in 1897.

## Atomic structure
The electron orbits around the atomic nucleus and determines the chemical properties of elements.
            """
            
            return {
                'data': [{
                    'content': test_content.strip(),
                    'images': {},
                    'metadata': {'document_name': 'electron_test.txt', 'page': 0}
                }]
            }
            
        except Exception as fallback_error:
            print(f"❌ Fallback error: {fallback_error}")
            return None
```


```python
parsed_pdf = download_wikipedia_pdf()

```

> ```
> ⬇️  Downloading Wikipedia PDF on electron...
> ✅ PDF downloaded successfully!
> 📊 PDF size: 2,147,884 bytes
> 🔄 Parsing PDF with Albert API...
> ✅ PDF parsed successfully!
> 📝 Content preview (9149 characters):
> ![](_page_0_Picture_0.jpeg)
> 
> ## **Électron**
> 
> L'**électron**, un des composants de l'[atome](https://fr.wikipedia.org/wiki/Atome) avec les [neutrons](https://fr.wikipedia.org/wiki/Neutron) et les [protons,](https://fr.wikipedia.org/wiki/Proton) est une [particule élémentaire](https://fr.wikipedia.or...
> ```

# 2.5. DETAILED DISPLAY OF PARSED CONTENT

Let's display the obtained result


```python
def display_first_page_content(parsed_data: Dict[str, Any]):
    """Displays the content of the first page in detail with images."""
    if not parsed_data or not parsed_data.get('data'):
        print("❌ No parsed content available")
        return
    
    # Take only the first page
    page_data = parsed_data['data'][0]
    
    print("📄 === FIRST PAGE ===")
    
    # Display markdown content
    content = page_data.get('content', '')
    print(f"\n📝 MARKDOWN CONTENT ({len(content)} characters):")
    print("=" * 60)
    print(content)
    print("=" * 60)
    
    # Display images
    images = page_data.get('images', {})
    if images:
        print(f"\n🖼️  DETECTED IMAGES ({len(images)} images):")
        print("-" * 40)
        
        # Import libraries to display images
        if JUPYTER_AVAILABLE:
            # Jupyter environment - direct image display
            for img_name, img_data in images.items():
                print(f"📸 Image: {img_name}")
                
                try:
                    # Decode base64 image
                    img_bytes = base64.b64decode(img_data)
                    print(f"   ✅ Image decoded: {len(img_bytes):,} bytes")
                    
                    # Display image in Jupyter
                    display(Image(data=img_bytes))
                    
                except Exception as e:
                    print(f"   ❌ Image decoding error {img_name}: {e}")
                    print(f"   Type: {'JPEG' if img_data.startswith('/9j/') else 'PNG/Other'}")
                    print(f"   Base64 size: {len(img_data):,} characters")
                    
                print()
        else:
            # Standard environment - HTML display
            print("⚠️  HTML image display (copy HTML code into a browser):")
            
            for img_name, img_data in images.items():
                print(f"📸 Image: {img_name}")
                
                # Determine image format
                if img_data.startswith('/9j/'):
                    img_format = "jpeg"
                elif img_data.startswith('iVBOR'):
                    img_format = "png"
                else:
                    img_format = "jpeg"  # Default
                
                print(f"   Type: {img_format.upper()}")
                print(f"   Base64 size: {len(img_data):,} characters")
                
                # Create an HTML tag to display the image
                html_img = f'<img src="data:image/{img_format};base64,{img_data}" style="max-width:500px; max-height:400px; border:1px solid #ccc; margin:10px;" alt="{img_name}">'
                print("   📋 HTML code for display:")
                print(f"   {html_img}")
                print()
    else:
        print("🖼️  No images detected on this page")
    
    # Display important metadata
    metadata = page_data.get('metadata', {})
    if metadata:
        print("\n📊 MAIN METADATA:")
        print("-" * 30)
        
        # Basic information
        doc_name = metadata.get('document_name', 'N/A')
        page_num = metadata.get('page', 'N/A')
        print(f"   📄 Document: {doc_name}")
        print(f"   📝 Page: {page_num}")
        
        # Table of contents if present
        if 'table_of_contents' in metadata and metadata['table_of_contents']:
            toc = metadata['table_of_contents']
            print(f"\n📋 TABLE OF CONTENTS ({len(toc)} entries):")
            for i, entry in enumerate(toc[:5]):  # Limit to 5 entries for the first page
                title = entry.get('title', 'No title')
                level = entry.get('heading_level', 'N/A')
                print(f"   {i+1}. {title} (level: {level})")
            if len(toc) > 5:
                print(f"   ... and {len(toc) - 5} other entries")
        
        # Parsing statistics
        if 'page_stats' in metadata:
            stats = metadata['page_stats']
            if stats and len(stats) > 0:
                page_stat = stats[0]
                method = page_stat.get('text_extraction_method', 'N/A')
                print("\n🔧 PARSING:")
                print(f"   Method: {method}")
                
                if 'block_counts' in page_stat:
                    print(f"   Detected blocks: {len(page_stat['block_counts'])}")
    
    print("\n" + "="*60)

if parsed_pdf:
    display_first_page_content(parsed_pdf)
else:
    print("❌ Unable to display content - parsing failed")
```

> ```
> 📄 === FIRST PAGE ===
> 
> 📝 MARKDOWN CONTENT (9149 characters):
> ============================================================
> ![](_page_0_Picture_0.jpeg)
> 
> ## **Électron**
> 
> L'**électron**, un des composants de l'[atome](https://fr.wikipedia.org/wiki/Atome) avec les [neutrons](https://fr.wikipedia.org/wiki/Neutron) et les [protons,](https://fr.wikipedia.org/wiki/Proton) est une [particule élémentaire](https://fr.wikipedia.org/wiki/Particule_%C3%A9l%C3%A9mentaire) qui possède une [charge élémentaire](https://fr.wikipedia.org/wiki/Charge_%C3%A9l%C3%A9mentaire) de signe négatif. Il est fondamental en [chimie,](https://fr.wikipedia.org/wiki/Chimie) car il participe à presque tous les types de [réactions chimiques](https://fr.wikipedia.org/wiki/R%C3%A9action_chimique) et constitue un élément primordial des [liaisons](https://fr.wikipedia.org/wiki/Liaison_chimique) présentes dans les [molécules](https://fr.wikipedia.org/wiki/Mol%C3%A9cule). En [physique,](https://fr.wikipedia.org/wiki/Physique) l'électron intervient dans une multitude de [rayonnements](https://fr.wikipedia.org/wiki/Rayonnement_%C3%A9lectromagn%C3%A9tique) et d'effets. Ses propriétés, qui se manifestent à l'échelle microscopique, expliquent la [conductivité](https://fr.wikipedia.org/wiki/Conductivit%C3%A9_%C3%A9lectrique) [électrique,](https://fr.wikipedia.org/wiki/Conductivit%C3%A9_%C3%A9lectrique) la [conductivité thermique,](https://fr.wikipedia.org/wiki/Conductivit%C3%A9_thermique) l'[effet Tcherenkov](https://fr.wikipedia.org/wiki/Effet_Tcherenkov), l'[incandescence,](https://fr.wikipedia.org/wiki/Incandescence) l['induction électromagnétique](https://fr.wikipedia.org/wiki/Induction_%C3%A9lectromagn%C3%A9tique), la [luminescence](https://fr.wikipedia.org/wiki/Luminescence), le [magnétisme,](https://fr.wikipedia.org/wiki/Magn%C3%A9tisme) le [rayonnement électromagnétique,](https://fr.wikipedia.org/wiki/Rayonnement_%C3%A9lectromagn%C3%A9tique) la [réflexion optique,](https://fr.wikipedia.org/wiki/R%C3%A9flexion_(optique)) l'[effet](https://fr.wikipedia.org/wiki/Effet_photovolta%C3%AFque) [photovoltaïque](https://fr.wikipedia.org/wiki/Effet_photovolta%C3%AFque) et la [supraconductivité,](https://fr.wikipedia.org/wiki/Supraconductivit%C3%A9) phénomènes macroscopiques largement exploités dans les industries. Possédant la plus faible masse de toutes les particules chargées, il sert régulièrement à l'étude de la matière.
> 
> Le concept d'une quantité indivisible de charge électrique est élaboré à partir de 1838 par le naturaliste britannique [Richard Laming](https://fr.wikipedia.org/wiki/Richard_Laming) afin d'expliquer les propriétés chimiques des [atomes](https://fr.wikipedia.org/wiki/Atome). L'électron est identifié comme le corpuscule envisagé par [Joseph John Thomson](https://fr.wikipedia.org/wiki/Joseph_John_Thomson) et son équipe de physiciens britanniques en 1897, à la suite de leurs travaux sur les [rayons](https://fr.wikipedia.org/wiki/Rayons_cathodiques) [cathodiques](https://fr.wikipedia.org/wiki/Rayons_cathodiques).
> 
> C'est à cette époque que Thomson propose [son modèle atomique.](https://fr.wikipedia.org/wiki/Mod%C3%A8le_atomique_de_Thomson) En 1905, [Albert Einstein](https://fr.wikipedia.org/wiki/Albert_Einstein) propose une explication de l'[effet photoélectrique](https://fr.wikipedia.org/wiki/Effet_photo%C3%A9lectrique) — des électrons émis par la matière sous l'influence de la lumière — qui servira d'argument en faveur de la [théorie des quanta.](https://fr.wikipedia.org/wiki/Th%C3%A9orie_des_quanta) En 1912, [Niels Bohr](https://fr.wikipedia.org/wiki/Niels_Bohr) explique les [raies spectrales](https://fr.wikipedia.org/wiki/Raie_spectrale) en postulant la [quantification de l'orbite des](https://fr.wikipedia.org/wiki/Mod%C3%A8le_de_Bohr) [électrons de l'atome hydrogène](https://fr.wikipedia.org/wiki/Mod%C3%A8le_de_Bohr), autre argument soutenant cette théorie. En 1914, les expériences d'[Ernest Rutherford](https://fr.wikipedia.org/wiki/Ernest_Rutherford) et d'autres ont solidement établi la structure de l'atome comme un noyau positivement chargé entouré d'électrons de masse plus faible. En 1923, les [résultats expérimentaux](https://fr.wikipedia.org/wiki/Diffusion_Compton) d'[Arthur Compton](https://fr.wikipedia.org/wiki/Arthur_Compton) convainquent une majorité de physiciens de la validité de la théorie des quanta. En 1924, [Wolfgang Pauli](https://fr.wikipedia.org/wiki/Wolfgang_Pauli) définit le [principe](https://fr.wikipedia.org/wiki/Principe_d%27exclusion_de_Pauli) [d'exclusion de Pauli](https://fr.wikipedia.org/wiki/Principe_d%27exclusion_de_Pauli), ce qui implique que les électrons possèdent un [spin.](https://fr.wikipedia.org/wiki/Spin) La même année, [Louis de Broglie](https://fr.wikipedia.org/wiki/Louis_de_Broglie) émet l'hypothèse, vérifiée plus tard, que les électrons présentent une [dualité onde-corpuscule.](https://fr.wikipedia.org/wiki/Dualit%C3%A9_onde-corpuscule) En 1928, [Paul Dirac](https://fr.wikipedia.org/wiki/Paul_Dirac) publie [son modèle de l'électron](https://fr.wikipedia.org/wiki/%C3%89quation_de_Dirac) qui l'amènera à prédire l'existence du [positon](https://fr.wikipedia.org/wiki/Positon) puis de l'[antimatière](https://fr.wikipedia.org/wiki/Antimati%C3%A8re). D'autres études des propriétés de l'électron ont mené à des théories plus complètes de la matière et du rayonnement.
> 
> ## **Histoire**
> 
> Les [anciens Grecs](https://fr.wikipedia.org/wiki/Gr%C3%A8ce_antique) ont déjà remarqué que l'[ambre](https://fr.wikipedia.org/wiki/Ambre) attire de petits objets quand il est frotté avec de la fourrure ; en dehors de la [foudre,](https://fr.wikipedia.org/wiki/Foudre) ce phénomène est la plus ancienne expérience de l'humanité en rapport avec l['électricité](https://fr.wikipedia.org/wiki/%C3%89lectricit%C3%A9) , un déplacement de particules électriquement chargées. [6](#page-17-2)
> 
> En 1269, [Pierre de Maricourt](https://fr.wikipedia.org/wiki/Pierre_de_Maricourt), un ingénieur militaire au service du prince français [Charles I](https://fr.wikipedia.org/wiki/Charles_Ier_d%27Anjou) er de Sicile, étudie les propriétés des [aimants permanents.](https://fr.wikipedia.org/wiki/Aimant) « Cette étude, qui nous a été transmise sous forme d'une lettre écrite à l'un de ses collègues, comprend la plupart des expériences élémentaires
> 
> ![](_page_0_Picture_8.jpeg)
> 
> Des expériences menées avec les tubes de [Crookes](https://fr.wikipedia.org/wiki/Tube_de_Crookes) ont démontré avec certitude l'existence de l'électron. Sur la photo, le tube est rempli d'un gaz à basse pression. Une tension électrique élevée est appliquée entre la cathode (à l'extrémité gauche) et l'anode (à l'extrémité du coude sous le tube). À la cathode, cette tension fait naître un faisceau de particules qui se déplacent en ligne droite (la faible lueur bleue au centre du tube), tant qu'ils ne heurtent pas d'atomes de gaz. À la droite, une pièce métallique en forme de [croix](https://fr.wikipedia.org/wiki/Croix_de_Malte_(symbole)) de [Malte](https://fr.wikipedia.org/wiki/Croix_de_Malte_(symbole)) bloque en partie ce flux, ce qui crée une ombre à l'extrémité droite. Les autres particules frappent le fond du tube et le rendent en partie [luminescent](https://fr.wikipedia.org/wiki/Luminescence) (lueur vert pâle). Dans
> 
> le coude sous le tube, le gaz s'illumine (lueur bleue) au passage des particules déviées, collectées par l'anode. Ces particules seront ensuite identifiées comme des électrons . [1](#page-17-0)
> 
> | Propriétés générales |                                                                                                                |
> |----------------------|----------------------------------------------------------------------------------------------------------------|
> | Classification       | Particule élémentaire                                                                                          |
> | Famille              | Fermion                                                                                                        |
> | Groupe               | Lepton                                                                                                         |
> | Génération           | re<br>1                                                                                                        |
> | Interaction(s)       | Gravité<br>Faible<br>Électromagnétique                                                                         |
> | Symbole              | −<br>e<br>−<br>β<br>(particule β)                                                                              |
> | Nbr. de types        | 1                                                                                                              |
> | Antiparticule        | positon                                                                                                        |
> | Propriétés physiques |                                                                                                                |
> | Masse                | −31 k<br>9,109 383 713 9(28) ×10<br>2<br>g ou<br>−31 k<br>9,109 383 701 5(28) ×10<br>g<br>2<br>(511 keV/c<br>) |
> | Charge<br>électrique | -1 e<br>−19 C<br>(−1,602 ×10<br>; selon<br>CODATA 2010, elle est de                                            |
> ============================================================
> 
> 🖼️  DETECTED IMAGES (2 images):
> ----------------------------------------
> 📸 Image: _page_0_Picture_0.jpeg
>    ✅ Image decoded: 6,654 bytes
> ```


> ```

> ```![jpeg](output_15_1.jpg)
> ```

> ```

> ```
> 📸 Image: _page_0_Picture_8.jpeg
>    ✅ Image decoded: 15,741 bytes
> ```


> ```

> ```![jpeg](output_15_3.jpg)
> ```

> ```

> ```
> 📊 MAIN METADATA:
> ------------------------------
>    📄 Document: electron_wikipedia.pdf
>    📝 Page: 0
> 
> 📋 TABLE OF CONTENTS (2 entries):
>    1. Électron (level: None)
>    2. Histoire (level: None)
> 
> 🔧 PARSING:
>    Method: pdftext
>    Detected blocks: 7
> 
> ============================================================
> ```

# 3. CREATING A COLLECTION

We are satisfied with the result of the first page, now we are going to store the document text in the database using the document endpoint. First, we need to create a collection using the collection endpoint.


```python
def create_collection(name: str, description: str) -> Optional[str]:
    """Creates a new collection."""
    try:
        collection_data = {
            "name": name,
            "description": description,
            "visibility": "private"
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/collections",
            headers={**headers, "Content-Type": "application/json"},
            json=collection_data
        )
        response.raise_for_status()
        
        collection_id = response.json()
        print(f"✅ Collection created with ID: {collection_id}")
        return collection_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating collection: {e}")
        return None

collection_id = create_collection(
    "Physical Sciences", 
    "Collection for storing and analyzing scientific documents"
)
```

> ```
> ✅ Collection created with ID: {'id': 4}
> ```

# 4. ADDING THE DOCUMENT TO THE COLLECTION


```python
def add_document_to_collection(collection_id: Any) -> Optional[Dict[str, Any]]:
    """Downloads the Wikipedia PDF and adds it directly to a collection for embedding."""
    try:
        print("⬇️  Re-downloading Wikipedia PDF to add to collection...")
        
        # Re-download PDF from Wikipedia REST API
        wikipedia_url = "https://fr.wikipedia.org/api/rest_v1/page/pdf/Électron"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Albert-API-Demo/1.0)'
        }
        
        pdf_response = requests.get(wikipedia_url, headers=headers, timeout=30)
        pdf_response.raise_for_status()
        
        print(f"✅ PDF re-downloaded: {len(pdf_response.content):,} bytes")
        
        # Send PDF directly to documents endpoint
        # Use all required parameters according to documentation
        files = {
            'file': ('electron_wikipedia.pdf', pdf_response.content, 'application/pdf')
        }
        
        # Complete parameters according to documentation
        # Note: for multipart/form-data, all parameters must be strings
        # Extract ID if collection_id is a dictionary
        collection_int_id = collection_id['id'] if isinstance(collection_id, dict) and 'id' in collection_id else collection_id
        
        data = {
            'collection': str(collection_int_id),  # Extract ID from dictionary and convert to string
            'output_format': 'markdown',
            'force_ocr': 'false',
            'languages': 'fr',
            'chunk_size': '1000',
            'chunk_overlap': '200',
            'use_llm': 'false',
            'paginate_output': 'false',
            'chunker': 'RecursiveCharacterTextSplitter',
            'length_function': 'len',
            'chunk_min_size': '0',
            'is_separator_regex': 'false',
            'metadata': ''
        }
        
        print("📤 Sending PDF to documents endpoint for parsing and embedding...")
        print(f"🔧 Parameters: collection={data['collection']}, chunk_size={data['chunk_size']}")
        
        response = requests.post(
            f"{BASE_URL}/v1/documents",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files=files,
            data=data
        )
        
        # Debug: display error details if it persists
        if not response.ok:
            print(f"❌ HTTP Error {response.status_code}")
            try:
                error_detail = response.json()
                print(f"📋 Error details: {error_detail}")
            except:
                print(f"📋 Raw response: {response.text}")
        
        response.raise_for_status()
        
        document_data = response.json()
        print(f"✅ Document added with ID: {document_data['id']}")
        print("🔄 Albert API performed parsing and embedding automatically")
        return document_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error adding document: {e}")
        
        # Fallback with test content
        try:
            print("🔄 Using test content as fallback...")
            
            test_content = """# The Electron

The electron is a stable elementary particle from the lepton family. 
It carries a negative elementary electric charge and has a rest mass 
of approximately 9.109 × 10⁻³¹ kg. The electron plays a fundamental role in chemistry, 
as it participates in chemical bonds.

## Main properties
- Charge: -1.602 × 10⁻¹⁹ coulombs
- Mass: 9.109 × 10⁻³¹ kg
- Spin: 1/2

## Discovery
The electron was discovered by J.J. Thomson in 1897.

## Atomic structure
The electron orbits around the atomic nucleus and determines the chemical properties of elements.
It participates in ionic and covalent bonds that form molecules."""
            
            file_content = test_content.encode('utf-8')
            
            files = {
                'file': ('electron_test.txt', file_content, 'text/plain')
            }
            
            data = {
                'collection': str(collection_int_id),  # Use the same extracted ID
                'chunk_size': '1000',
                'chunk_overlap': '200',
                'chunker': 'RecursiveCharacterTextSplitter',
                'length_function': 'len',
                'chunk_min_size': '0',
                'is_separator_regex': 'false',
                'metadata': ''
            }
            
            response = requests.post(
                f"{BASE_URL}/v1/documents",
                headers={"Authorization": f"Bearer {API_KEY}"},
                files=files,
                data=data
            )
            
            if not response.ok:
                print(f"❌ Fallback HTTP Error {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"📋 Fallback error details: {error_detail}")
                except:
                    print(f"📋 Raw fallback response: {response.text}")
            
            response.raise_for_status()
            
            document_data = response.json()
            print(f"✅ Test document added with ID: {document_data['id']}")
            return document_data
            
        except Exception as fallback_error:
            print(f"❌ Fallback error: {fallback_error}")
            return None

if collection_id:
    document_data = add_document_to_collection(collection_id)
    
    # Wait a bit for embedding to complete
    print("⏳ Waiting for embedding process to complete...")
    time.sleep(5)
```

> ```
> ⬇️  Re-downloading Wikipedia PDF to add to collection...
> ✅ PDF re-downloaded: 2,147,884 bytes
> 📤 Sending PDF to documents endpoint for parsing and embedding...
> 🔧 Parameters: collection=4, chunk_size=1000
> ✅ Document added with ID: 6
> 🔄 Albert API performed parsing and embedding automatically
> ⏳ Waiting for embedding process to complete...
> ```

# 5. SEMANTIC SEARCH

We use the search endpoint which allows us to retrieve the results that are semantically closest to the question in the collection.


```python
def semantic_search(query: str, collection_id: Any, k: int = 5) -> Optional[Dict[str, Any]]:
    """Performs a semantic search in the collection."""
    try:
        # Extract ID if collection_id is a dictionary
        collection_int_id = collection_id['id'] if isinstance(collection_id, dict) and 'id' in collection_id else collection_id
        
        search_data = {
            "collections": [collection_int_id],  # Use extracted ID
            "prompt": query,
            "k": k,
            "method": "semantic",
            "score_threshold": 0.1
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/search",
            headers={**headers, "Content-Type": "application/json"},
            json=search_data
        )
        response.raise_for_status()
        
        search_results = response.json()
        print(f"✅ Search performed: {len(search_results['data'])} results found")
        
        for i, result in enumerate(search_results['data'][:3], 1):
            print(f"\n📄 Result {i} (score: {result['score']:.3f}):")
            print(f"   {result['chunk']['content'][:200]}...")
        
        return search_results
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during search: {e}")
        return None
```


```python
QUESTION = "Quelles sont les principales propriétés physiques de l'électron et qui l'a découvert ?"
print(f"❓ Question: {QUESTION}")

if collection_id:
    search_results = semantic_search(QUESTION, collection_id)
```

> ```
> ❓ Question: Quelles sont les principales propriétés physiques de l'électron et qui l'a découvert ?
> ✅ Search performed: 5 results found
> 
> 📄 Result 1 (score: 0.647):
>    . Il montre que le rapport charge sur masse *e/m* est indépendant de la matière de la cathode. Il montre de plus que les particules chargées négativement produites par les matériaux radioactifs, les m...
> 
> 📄 Result 2 (score: 0.636):
>    En 1887, l'[effet photoélectrique](https://fr.wikipedia.org/wiki/Effet_photo%C3%A9lectrique) est observé par [Heinrich Hertz](https://fr.wikipedia.org/wiki/Heinrich_Hertz) alors qu'il étudie les [onde...
> 
> 📄 Result 3 (score: 0.632):
>    En 1894, Stoney invente le terme d'« électron » pour désigner ces charges élémentaires, écrivant « […] une estimation a été faite de la valeur réelle de cette unité fondamentale très remarquable d'éle...
> ```

# 6. RESPONSE GENERATION WITH RAG

We can also use the chat/completion endpoint with RAG enabled on the collection to directly generate the answer to the question.


```python

def chat_with_rag(question: str, collection_id: Any, chat_model: str) -> Optional[str]:
    """Utilise le chat completion avec RAG activé."""
    try:
        # Extraire l'ID si collection_id est un dictionnaire
        collection_int_id = collection_id['id'] if isinstance(collection_id, dict) and 'id' in collection_id else collection_id
        
        chat_data = {
            "messages": [
                {
                    "role": "user",
                    "content": question
                }
            ],
            "model": chat_model,
            "temperature": 0.3,
            "max_completion_tokens": 500,
            "search": True,
            "search_args": {
                "collections": [collection_int_id],  # Utiliser l'ID extrait
                "k": 5,
                "method": "semantic",
                "score_threshold": 0.1,
                "template": "Réponds à la question suivante en te basant sur les documents ci-dessous : {prompt}\n\nDocuments :\n{chunks}"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={**headers, "Content-Type": "application/json"},
            json=chat_data
        )
        response.raise_for_status()
        
        chat_response = response.json()
        
        if chat_response.get('choices') and len(chat_response['choices']) > 0:
            answer = chat_response['choices'][0]['message']['content']
            print("✅ Réponse générée:")
            print(f"🎯 {answer}")
            
            # Affichage des informations sur l'usage
            if 'usage' in chat_response:
                usage = chat_response['usage']
                print("\n📊 Usage:")
                print(f"   Tokens prompt: {usage.get('prompt_tokens', 0)}")
                print(f"   Tokens completion: {usage.get('completion_tokens', 0)}")
                print(f"   Total tokens: {usage.get('total_tokens', 0)}")
                if 'cost' in usage:
                    print(f"   Coût: {usage['cost']}")
            
            # Affichage des résultats de recherche utilisés
            if 'search_results' in chat_response:
                print(f"\n🔍 {len(chat_response['search_results'])} documents utilisés pour le contexte")
            
            return answer
        else:
            print("❌ Aucune réponse générée")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors du chat: {e}")
        return None

if collection_id and chat_model:
    final_answer = chat_with_rag(QUESTION, collection_id, chat_model)
```

> ```
> ✅ Réponse générée:
> 🎯 Selon les documents fournis, les principales propriétés physiques de l'électron sont :
> 
> 1.  Il possède un spin, ce qui est décrit par le principe d'exclusion de Pauli.
> 2.  Il présente une dualité onde-corpuscule, ce qui signifie qu'il se comporte à la fois comme une particule et comme une onde.
> 3.  Il a une longueur d'onde de De Broglie caractéristique donnée par λe = h/p, où h est la constante de Planck et p est la quantité de mouvement.
> 4.  Il peut être détruit lors de la capture électronique qui survient dans les noyaux d'atomes radioactifs.
> 
> Quant à la découverte de l'électron, elle est attribuée à plusieurs scientifiques, notamment :
> 
> 1.  Le physicien irlandais George F. Fitzgerald, qui propose le nom d'électron avec succès.
> 2.  Le physicien anglais J.J. Thomson, qui a réalisé des expériences sur la déflexion des rayons cathodiques dans un champ électrique et a montré que les particules chargées négativement produites par les matériaux radioactifs, les matières chauffées et les matières illuminées sont les mêmes.
> 3.  Le physicien anglais Joseph John Thomson, qui a découvert l'électron en 1897 en étudiant la déflexion des rayons cathodiques dans un champ électrique.
> 
> Le terme d'électron a été inventé par George Johnstone Stoney en 1894.
> 
> 📊 Usage:
>    Tokens prompt: 1302
>    Tokens completion: 305
>    Total tokens: 1607
>    Coût: 0.0
> 
> 🔍 5 documents utilisés pour le contexte
> ```

# 7. SUMMARY AND CLEANUP


```python
print("✅ Completed steps:")
print("   1. ✓ Retrieved available models")
print("   2. ✓ Downloaded and parsed Wikipedia PDF")
print("   3. ✓ Created a collection")
print("   4. ✓ Added document with embedding")
print("   5. ✓ Semantic search")
print("   6. ✓ Generated response with RAG")

print(f"\n🎯 Question asked: {QUESTION}")
if 'final_answer' in locals() and final_answer:
    print(f"💡 Answer obtained: {final_answer}")

print("\n🧹 Cleanup (optional)")
if collection_id:
    # Extract ID for display
    display_id = collection_id['id'] if isinstance(collection_id, dict) and 'id' in collection_id else collection_id
    print("To delete the created collection, use:")
    print(f"DELETE {BASE_URL}/v1/collections/{display_id}")
else:
    print("No collection created to clean up")

print("\n" + "=" * 50)
print("🎉 Demonstration completed!")
print("This notebook showed how to use the Albert API to:")
print("- Parse PDF documents from Wikipedia")
print("- Create collections and perform embedding")
print("- Perform semantic searches")
print("- Generate contextualized responses with RAG")
```

> ```
> ✅ Completed steps:
>    1. ✓ Retrieved available models
>    2. ✓ Downloaded and parsed Wikipedia PDF
>    3. ✓ Created a collection
>    4. ✓ Added document with embedding
>    5. ✓ Semantic search
>    6. ✓ Generated response with RAG
> 
> 🎯 Question asked: Quelles sont les principales propriétés physiques de l'électron et qui l'a découvert ?
> 💡 Answer obtained: Selon les documents fournis, les principales propriétés physiques de l'électron sont :
> 
> 1.  Il possède un spin, ce qui est décrit par le principe d'exclusion de Pauli.
> 2.  Il présente une dualité onde-corpuscule, ce qui signifie qu'il se comporte à la fois comme une particule et comme une onde.
> 3.  Il a une longueur d'onde de De Broglie caractéristique donnée par λe = h/p, où h est la constante de Planck et p est la quantité de mouvement.
> 4.  Il peut être détruit lors de la capture électronique qui survient dans les noyaux d'atomes radioactifs.
> 
> Quant à la découverte de l'électron, elle est attribuée à plusieurs scientifiques, notamment :
> 
> 1.  Le physicien irlandais George F. Fitzgerald, qui propose le nom d'électron avec succès.
> 2.  Le physicien anglais J.J. Thomson, qui a réalisé des expériences sur la déflexion des rayons cathodiques dans un champ électrique et a montré que les particules chargées négativement produites par les matériaux radioactifs, les matières chauffées et les matières illuminées sont les mêmes.
> 3.  Le physicien anglais Joseph John Thomson, qui a découvert l'électron en 1897 en étudiant la déflexion des rayons cathodiques dans un champ électrique.
> 
> Le terme d'électron a été inventé par George Johnstone Stoney en 1894.
> 
> 🧹 Cleanup (optional)
> To delete the created collection, use:
> DELETE http://localhost:8000/v1/collections/4
> 
> ==================================================
> 🎉 Demonstration completed!
> This notebook showed how to use the Albert API to:
> - Parse PDF documents from Wikipedia
> - Create collections and perform embedding
> - Perform semantic searches
> - Generate contextualized responses with RAG
> ```
