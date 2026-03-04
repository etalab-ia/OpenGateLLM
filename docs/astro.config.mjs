// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { fileURLToPath } from 'node:url';
import { ion } from 'starlight-ion-theme';
import starlightGiscus from 'starlight-giscus';
import starlightScrollToTop from 'starlight-scroll-to-top';
import starlightLinksValidator from 'starlight-links-validator'
import mermaid from 'astro-mermaid';

// https://astro.build/config
export default defineConfig({
	integrations: [
		mermaid({
			theme: 'forest',
			autoTheme: true,
			iconPacks: [
				{
				  name: 'logos',
				  loader: () => fetch('https://unpkg.com/@iconify-json/logos@1/icons.json').then(res => res.json())
				},
				{
					name: 'lobe',
					loader: () => fetch('https://unpkg.com/@proj-airi/lobe-icons@latest/icons.json').then((res) => res.json()),
				},
			  ]
		}),
		starlight({
			title: 'OpenGateLLM',
			editLink: {
				baseUrl: 'https://github.com/etalab-ia/OpenGateLLM/edit/main/docs',
			},
			components: {
				Pagination: './src/components/Pagination.astro',
			},
			logo: {
				src: './src/assets/logo.svg',
			},			
			social: [
				{   
					icon: 'github', 
					label: 'GitHub',
					href: 'https://github.com/etalab-ia/OpenGateLLM' 
				}
			],
			plugins: [
				ion({
					icons: {
						iconDir: fileURLToPath(new URL('./src/assets/icons', import.meta.url)),
						include: { lucide: ['*'], lobe: ['*'] },
					},
				}),
				starlightGiscus({
					repo: 'etalab-ia/OpenGateLLM',
					repoId: 'R_kgDOMT6C-w',
					category: 'General',
					categoryId: 'DIC_kwDOMT6C-84CkkTP'
				}),
				starlightScrollToTop(),
				starlightLinksValidator(
					{
						errorOnLocalLinks: false,
						// `/reference/` is generated from `redoc-static.html` via a custom Astro route.
						// Exclude it from link validation because this plugin cannot resolve that custom page.
						exclude: ['/reference', '/reference/'],
					},
				),
			],
			sidebar: [
				{ 
					label: 'Overview',
					autogenerate: {
						directory: 'overview',
					},
				},
				{
					label: '[lucide:mountain]Roadmap',
					link: 'https://github.com/etalab-ia/OpenGateLLM/milestone/4',
					attrs: { target: '_blank', style: 'font-size: 0.875rem;' },
				},
				{
					label: '[lucide:book-open] API reference',
					link: '/reference/',
					attrs: { target: '_blank', style: 'font-size: 0.875rem;' },
				},				{
					label: '[lucide:rocket] Release notes',
					link: 'https://github.com/etalab-ia/OpenGateLLM/releases',
					badge: 'v0.4.1',
					attrs: { target: '_blank', style: 'font-size: 0.875rem;' },
				},
				{
					label: 'Getting started',
					autogenerate: {
						directory: 'getting-started',
					},
				},
				{
					label: 'Advanced configuration',
					autogenerate: {
						directory: 'configuration',
					},
				},
				{
					label: 'Deployment',
					autogenerate: {
						directory: 'deployment',
					},
				},
				{
					label: 'Features',
					autogenerate: {
						directory: 'features',
					},
				},
				{
					label: 'Contributing',
					items: [
						{ label: '[lucide:book-open] Contributing guide', autogenerate: { directory: 'contributing' } },
					],
				},
			],
		}),
	],
});
