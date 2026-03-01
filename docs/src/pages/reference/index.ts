import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

export const prerender = true;

export async function GET() {
	const html = await readFile(resolve(process.cwd(), 'redoc-static.html'), 'utf-8');
	return new Response(html, {
		headers: {
			'Content-Type': 'text/html; charset=utf-8',
		},
	});
}
