import * as spectralCore from '@stoplight/spectral-core';
import { createRulesetFunction } from '@stoplight/spectral-core';

function getAugmentedNamespace(n) {
  if (n.__esModule) return n;
  var f = n.default;
	if (typeof f == "function") {
		var a = function a () {
			if (this instanceof a) {
				var args = [null];
				args.push.apply(args, arguments);
				var Ctor = Function.bind.apply(f, args);
				return new Ctor();
			}
			return f.apply(this, arguments);
		};
		a.prototype = f.prototype;
  } else a = {};
  Object.defineProperty(a, '__esModule', {value: true});
	Object.keys(n).forEach(function (k) {
		var d = Object.getOwnPropertyDescriptor(n, k);
		Object.defineProperty(a, k, d.get ? d : {
			enumerable: true,
			get: function () {
				return n[k];
			}
		});
	});
	return a;
}

var serverVariables = {};

var require$$0 = /*@__PURE__*/getAugmentedNamespace(spectralCore);

var parseUrlVariables$1 = {};

Object.defineProperty(parseUrlVariables$1, "__esModule", { value: true });
parseUrlVariables$1.parseUrlVariables = void 0;
function parseUrlVariables(str) {
    if (typeof str !== 'string')
        return [];
    const variables = str.match(/{(.+?)}/g);
    if (!variables || variables.length === 0)
        return [];
    return variables.map(v => v.slice(1, -1));
}
parseUrlVariables$1.parseUrlVariables = parseUrlVariables;

var getMissingProps$1 = {};

Object.defineProperty(getMissingProps$1, "__esModule", { value: true });
getMissingProps$1.getMissingProps = void 0;
function getMissingProps(arr, props) {
    return arr.filter(val => {
        return !props.includes(val);
    });
}
getMissingProps$1.getMissingProps = getMissingProps;

var getRedundantProps$1 = {};

Object.defineProperty(getRedundantProps$1, "__esModule", { value: true });
getRedundantProps$1.getRedundantProps = void 0;
function getRedundantProps(arr, keys) {
    return keys.filter(val => {
        return !arr.includes(val);
    });
}
getRedundantProps$1.getRedundantProps = getRedundantProps;

var applyUrlVariables$1 = {};

Object.defineProperty(applyUrlVariables$1, "__esModule", { value: true });
applyUrlVariables$1.applyUrlVariables = void 0;
function* applyUrlVariables(url, variables) {
    yield* _applyUrlVariables(url, 0, variables.map(toApplicableVariable));
}
applyUrlVariables$1.applyUrlVariables = applyUrlVariables;
function* _applyUrlVariables(url, i, variables) {
    const [name, values] = variables[i];
    let x = 0;
    while (x < values.length) {
        const substitutedValue = url.replace(name, values[x]);
        if (i === variables.length - 1) {
            yield substitutedValue;
        }
        else {
            yield* _applyUrlVariables(substitutedValue, i + 1, variables);
        }
        x++;
    }
}
function toApplicableVariable([name, values]) {
    return [toReplaceRegExp(name), values.map(encodeURI)];
}
function toReplaceRegExp(name) {
    return RegExp(escapeRegexp(`{${name}}`), 'g');
}
function escapeRegexp(value) {
    return value.replace(/[\\^$*+?.()|[\]{}]/g, '\\$&');
}

Object.defineProperty(serverVariables, "__esModule", { value: true });
const spectral_core_1 = require$$0;
const parseUrlVariables_1 = parseUrlVariables$1;
const getMissingProps_1 = getMissingProps$1;
const getRedundantProps_1 = getRedundantProps$1;
const applyUrlVariables_1 = applyUrlVariables$1;
export default createRulesetFunction({
    input: {
        errorMessage: 'Invalid Server Object',
        type: 'object',
        properties: {
            url: {
                type: 'string',
            },
            variables: {
                type: 'object',
                additionalProperties: {
                    type: 'object',
                    properties: {
                        enum: {
                            type: 'array',
                            items: {
                                type: 'string',
                            },
                        },
                        default: {
                            type: 'string',
                        },
                        description: {
                            type: 'string',
                        },
                        examples: {
                            type: 'string',
                        },
                    },
                    patternProperties: {
                        '^x-': true,
                    },
                    additionalProperties: false,
                },
            },
        },
        required: ['url'],
    },
    errorOnInvalidInput: true,
    options: {
        type: ['object', 'null'],
        properties: {
            checkSubstitutions: {
                type: 'boolean',
                default: 'false',
            },
        },
        additionalProperties: false,
    },
}, function serverVariables({ url, variables }, opts, ctx) {
    var _a;
    if (variables === void 0)
        return;
    const results = [];
    const foundVariables = (0, parseUrlVariables_1.parseUrlVariables)(url);
    const definedVariablesKeys = Object.keys(variables);
    const redundantVariables = (0, getRedundantProps_1.getRedundantProps)(foundVariables, definedVariablesKeys);
    for (const variable of redundantVariables) {
        results.push({
            message: `Server's "variables" object has unused defined "${variable}" url variable.`,
            path: [...ctx.path, 'variables', variable],
        });
    }
    if (foundVariables.length === 0)
        return results;
    const missingVariables = (0, getMissingProps_1.getMissingProps)(foundVariables, definedVariablesKeys);
    if (missingVariables.length > 0) {
        results.push({
            message: `Not all server's variables are described with "variables" object. Missed: ${missingVariables.join(', ')}.`,
            path: [...ctx.path, 'variables'],
        });
    }
    const variablePairs = [];
    for (const key of definedVariablesKeys) {
        if (redundantVariables.includes(key))
            continue;
        const values = variables[key];
        if ('enum' in values) {
            variablePairs.push([key, values.enum]);
            if ('default' in values && !values.enum.includes(values.default)) {
                results.push({
                    message: `Server Variable "${key}" has a default not listed in the enum`,
                    path: [...ctx.path, 'variables', key, 'default'],
                });
            }
        }
        else {
            variablePairs.push([key, [(_a = values.default) !== null && _a !== void 0 ? _a : '']]);
        }
    }
    if ((opts === null || opts === void 0 ? void 0 : opts.checkSubstitutions) === true && variablePairs.length > 0) {
        checkSubstitutions(results, ctx.path, url, variablePairs);
    }
    return results;
});
function checkSubstitutions(results, path, url, variables) {
    const invalidUrls = [];
    for (const substitutedUrl of (0, applyUrlVariables_1.applyUrlVariables)(url, variables)) {
        try {
            new URL(substitutedUrl);
        }
        catch {
            invalidUrls.push(substitutedUrl);
            if (invalidUrls.length === 5) {
                break;
            }
        }
    }
    if (invalidUrls.length === 5) {
        results.push({
            message: `At least 5 substitutions of server variables resulted in invalid URLs: ${invalidUrls.join(', ')} and more`,
            path: [...path, 'variables'],
        });
    }
    else if (invalidUrls.length > 0) {
        results.push({
            message: `A few substitutions of server variables resulted in invalid URLs: ${invalidUrls.join(', ')}`,
            path: [...path, 'variables'],
        });
    }
}
