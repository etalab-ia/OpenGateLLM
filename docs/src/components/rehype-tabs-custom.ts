import type { Element } from 'hast';
import { select } from 'hast-util-select';
import { rehype } from 'rehype';
import { CONTINUE, SKIP, visit } from 'unist-util-visit';

interface Panel {
	panelId: string;
	tabId: string;
	label: string;
	icon?: string;
}

declare module 'vfile' {
	interface DataMap {
		panels: Panel[];
	}
}

export const TabItemTagname = 'custom-tab-item';

// Copied from Starlight tabs focusable selectors.
const focusableElementSelectors = [
	'input:not([disabled]):not([type=hidden])',
	'select:not([disabled])',
	'textarea:not([disabled])',
	'button:not([disabled])',
	'a[href]',
	'area[href]',
	'summary',
	'iframe',
	'object',
	'embed',
	'audio[controls]',
	'video[controls]',
	'[contenteditable]',
	'[tabindex]:not([disabled])',
]
	.map((selector) => `${selector}:not([hidden]):not([tabindex="-1"])`)
	.join(',');

let count = 0;
const getIDs = () => {
	const id = count++;
	return { panelId: 'tab-panel-' + id, tabId: 'tab-' + id };
};

const tabsProcessor = rehype()
	.data('settings', { fragment: true })
	.use(function tabs() {
		return (tree: Element, file) => {
			file.data.panels = [];
			let isFirst = true;
			visit(tree, 'element', (node) => {
				if (node.tagName !== TabItemTagname || !node.properties) {
					return CONTINUE;
				}

				const { dataLabel, dataIcon } = node.properties;
				const ids = getIDs();
				const panel: Panel = {
					...ids,
					label: String(dataLabel),
				};
				if (dataIcon) panel.icon = String(dataIcon);
				file.data.panels?.push(panel);

				delete node.properties.dataLabel;
				delete node.properties.dataIcon;
				node.tagName = 'div';
				node.properties.id = ids.panelId;
				node.properties['aria-labelledby'] = ids.tabId;
				node.properties.role = 'tabpanel';

				const focusableChild = select(focusableElementSelectors, node);
				if (!focusableChild) {
					node.properties.tabindex = 0;
				}

				if (isFirst) {
					isFirst = false;
				} else {
					node.properties.hidden = true;
				}

				return SKIP;
			});
		};
	});

export const processPanels = (html: string) => {
	const file = tabsProcessor.processSync({ value: html });
	return {
		panels: file.data.panels,
		html: file.toString(),
	};
};
