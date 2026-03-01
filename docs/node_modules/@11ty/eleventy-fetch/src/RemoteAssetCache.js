const fs = require("fs");
const fsp = fs.promises; // Node 10+

const fetch = require("node-fetch");
const AssetCache = require("./AssetCache");
const debug = require("debug")("EleventyCacheAssets");

class RemoteAssetCache extends AssetCache {
	constructor(url, cacheDirectory, options = {}) {
		let cleanUrl = url;
		if(options.removeUrlQueryParams) {
			cleanUrl = RemoteAssetCache.cleanUrl(cleanUrl);
		}
		super(cleanUrl, cacheDirectory, options);

		this.url = url;
		this.options = options;

		// Important: runs after removeUrlQueryParams
		this.displayUrl = this.formatUrlForDisplay(cleanUrl);
	}

	static cleanUrl(url) {
		let cleanUrl = new URL(url);
		cleanUrl.search = new URLSearchParams([]);
		return cleanUrl.toString();
	}

	formatUrlForDisplay(url) {
		if(this.options.formatUrlForDisplay && typeof this.options.formatUrlForDisplay === "function") {
			return this.options.formatUrlForDisplay(url);
		}
		return url;
	}

	get url() {
		return this._url;
	}

	set url(url) {
		this._url = url;
	}

	async getResponseValue(response, type) {
		if(type === "json") {
			return response.json();
		} else if(type === "text") {
			return response.text();
		}
		return response.buffer();
	}

	async fetch(optionsOverride = {}) {
		let duration = optionsOverride.duration || this.options.duration;
		// Important: no disk writes when dryRun
		// As of Fetch v4, reads are now allowed!
		if(super.isCacheValid(duration) ) {
			this.log( `Cache hit for ${this.displayUrl}` );
			return super.getCachedValue();
		}

		try {
			let isDryRun = optionsOverride.dryRun || this.options.dryRun;
			this.log( `${isDryRun? "Fetching" : "Cache miss for"} ${this.displayUrl}`);

			let fetchOptions = optionsOverride.fetchOptions || this.options.fetchOptions || {};
			let response = await fetch(this.url, fetchOptions);
			if(!response.ok) {
				throw new Error(`Bad response for ${this.displayUrl} (${response.status}): ${response.statusText}`, { cause: response });
			}

			let type = optionsOverride.type || this.options.type;
			let body = await this.getResponseValue(response, type);
			if(!isDryRun) {
				await super.save(body, type);
			}
			return body;
		} catch(e) {
			if(this.cachedObject) {
				this.log( `Error fetching ${this.displayUrl}. Message: ${e.message}`);
				this.log( `Failing gracefully with an expired cache entry.` );
				return super.getCachedValue();
			} else {
				return Promise.reject(e);
			}
		}
	}

	// for testing
	hasCacheFiles() {
		return fs.existsSync(this.cachePath) ||
			fs.existsSync(this.getCachedContentsPath());
	}

	// for testing
	async destroy() {
		if(fs.existsSync(this.cachePath)) {
			await fsp.unlink(this.cachePath);
		}
		if(fs.existsSync(this.getCachedContentsPath())) {
			await fsp.unlink(this.getCachedContentsPath());
		}
	}
}
module.exports = RemoteAssetCache;