# OpenGateLLM documentation

OpenGateLLM uses `Docusaurus` to serve its documentation.

------------------------------------------------------------------------
## Installing and Running the project
### Documentation installation
Before you begin, make sure you have:

- **Node.js** (version 18+ recommended)
- **npm** (or **yarn/pnpm**) installed

Check your versions with:

``` bash
node -v
npm -v
```


Install dependencies:

``` bash
cd docs/
npm install
```


### Running the Development Server
Start the local development server:

``` bash
npm run start
```

This will:

-   Launch a development server at **http://localhost:3000/**
-   Hot-reload changes as you edit files

### Building for Production

You can build the website with:

``` bash
npm run build
```

The output will be in the `build/` folder, which you can deploy to any
static hosting service (Vercel, Netlify, GitHub Pages, etc.).

------------------------------------------------------------------------
## Project Structure Overview

The most importants files in the project are:

    docs/
     ├─ blog/             # Blog posts
     ├─ docs/             # Documentation pages
     ├─ src/              # Custom React components, pages, styles
     │   ├─ components/   # Reusable React components
     │   ├─ css/          # Custom Css
     │   ├─ pages/        # Custom pages (e.g., about.js)
     │   └─ theme/        # Custom theme
     ├─ static/           # Static assets (images, files)
     │   └─ img/          # Images used in the markdown in docs
     ├─ docusaurus.config.js  # Main configuration file
     └─ sidebars.js       # Defines sidebar navigation

------------------------------------------------------------------------
## Updating the documentation

### Editing the markdown

You can add or modify content to the documentation by adding or modifying the files inside the docs  `docs/` folder.
You can use either `.md` or `mdx` files.

### Updating the documentation sidebar
If you add a file, you'll need to add your page to the **sidebar**.

In `docs/sidebars.ts`, add an item to tutorialSidebar:

1. if your content is a single markdown (named `my_documentation.md`) outside a category, add:

```typescript
{
    type: 'doc',
    id: 'my_documentation',
}
```

2. if your content is a markdown (named `my_documentation.md)` inside a category (named my_category):


```typescript
{
    type: 'category',
    label: 'my_category',
    items:  [
                'my_documentation'
            ],
}
```

> Warning:
> If your markdown (`my_documentation.md`) is in a subdirectory in `docs` (for instance `functionalities`), the id of your page will be `functionalities/my_documentation`
------------------------------------------------------------------------

### Customizing Configuration

Open `docusaurus.config.js` to change:

-   **Site title & tagline**
-   **Navbar & footer links**
-   **Theme colors**
-   **Deployment settings**


------------------------------------------------------------------------
## Deploying documentation

When a file is modified in the `docs` folder, a new docker image of the documentation website is created [here](https://github.com/etalab-ia/OpenGateLLM/pkgs/container/opengatellm%2Fdocs) and the official documentation is automatically updated.
