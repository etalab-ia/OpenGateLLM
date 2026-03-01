const {default: PQueue} = require("p-queue");
const debug = require("debug")("EleventyCacheAssets");

const RemoteAssetCache = require("./src/RemoteAssetCache");
const AssetCache = require("./src/AssetCache");

const globalOptions = {
	type: "buffer",
	directory: ".cache",
	concurrency: 10,
	fetchOptions: {},
	dryRun: false, // don’t write anything to the file system

	// *does* affect cache key hash
	removeUrlQueryParams: false,

	// runs after removeUrlQueryParams, does not affect cache key hash
	// formatUrlForDisplay: function(url) {
	// 	return url;
	// },

	verbose: false, // Changed in 3.0+

	hashLength: 30,
};

function isFullUrl(url) {
	try {
		new URL(url);
		return true;
	} catch(e) {
		// invalid url OR already a local path
		return false;
	}
}

async function save(source, options) {
	if(!isFullUrl(source)) {
		return Promise.reject(new Error("Caching an already local asset is not yet supported."));
	}

	let asset = new RemoteAssetCache(source, options.directory, options);
	return asset.fetch(options);
}

/* Queue */
let queue = new PQueue({
	concurrency: globalOptions.concurrency
});

queue.on("active", () => {
	debug( `Concurrency: ${queue.concurrency}, Size: ${queue.size}, Pending: ${queue.pending}` );
});

let inProgress = {};

function queueSave(source, queueCallback) {
	if(!inProgress[source]) {
		inProgress[source] = queue.add(queueCallback).finally(() => {
			delete inProgress[source];
		});
	}
	
	return inProgress[source];
}

module.exports = function(source, options) {
	let mergedOptions = Object.assign({}, globalOptions, options);
	return queueSave(source, () => {
		return save(source, mergedOptions);
	});
};

Object.defineProperty(module.exports, "concurrency", {
	get: function() {
		return queue.concurrency;
	},
	set: function(concurrency) {
		queue.concurrency = concurrency;
	},
});

module.exports.queue = queueSave;
module.exports.Util = {
	isFullUrl
};
module.exports.RemoteAssetCache = RemoteAssetCache;
module.exports.AssetCache = AssetCache;
