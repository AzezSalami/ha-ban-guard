// node_modules/@lit/reactive-element/css-tag.js
var e = globalThis, t = e.ShadowRoot && (e.ShadyCSS === void 0 || e.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, n = Symbol(), r = /* @__PURE__ */ new WeakMap(), i = class {
	constructor(e, t, r) {
		if (this._$cssResult$ = !0, r !== n) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
		this.cssText = e, this.t = t;
	}
	get styleSheet() {
		let e = this.o, n = this.t;
		if (t && e === void 0) {
			let t = n !== void 0 && n.length === 1;
			t && (e = r.get(n)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), t && r.set(n, e));
		}
		return e;
	}
	toString() {
		return this.cssText;
	}
}, a = (e) => new i(typeof e == "string" ? e : e + "", void 0, n), o = (e, ...t) => new i(e.length === 1 ? e[0] : t.reduce((t, n, r) => t + ((e) => {
	if (!0 === e._$cssResult$) return e.cssText;
	if (typeof e == "number") return e;
	throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
})(n) + e[r + 1], e[0]), e, n), s = (n, r) => {
	if (t) n.adoptedStyleSheets = r.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
	else for (let t of r) {
		let r = document.createElement("style"), i = e.litNonce;
		i !== void 0 && r.setAttribute("nonce", i), r.textContent = t.cssText, n.appendChild(r);
	}
}, c = t ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((e) => {
	let t = "";
	for (let n of e.cssRules) t += n.cssText;
	return a(t);
})(e) : e, { is: l, defineProperty: u, getOwnPropertyDescriptor: ee, getOwnPropertyNames: te, getOwnPropertySymbols: ne, getPrototypeOf: re } = Object, d = globalThis, ie = d.trustedTypes, ae = ie ? ie.emptyScript : "", oe = d.reactiveElementPolyfillSupport, f = (e, t) => e, p = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? ae : null;
				break;
			case Object:
			case Array: e = e == null ? e : JSON.stringify(e);
		}
		return e;
	},
	fromAttribute(e, t) {
		let n = e;
		switch (t) {
			case Boolean:
				n = e !== null;
				break;
			case Number:
				n = e === null ? null : Number(e);
				break;
			case Object:
			case Array: try {
				n = JSON.parse(e);
			} catch {
				n = null;
			}
		}
		return n;
	}
}, m = (e, t) => !l(e, t), se = {
	attribute: !0,
	type: String,
	converter: p,
	reflect: !1,
	useDefault: !1,
	hasChanged: m
};
Symbol.metadata ??= Symbol("metadata"), d.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var h = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = se) {
		if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
			let n = Symbol(), r = this.getPropertyDescriptor(e, n, t);
			r !== void 0 && u(this.prototype, e, r);
		}
	}
	static getPropertyDescriptor(e, t, n) {
		let { get: r, set: i } = ee(this.prototype, e) ?? {
			get() {
				return this[t];
			},
			set(e) {
				this[t] = e;
			}
		};
		return {
			get: r,
			set(t) {
				let a = r?.call(this);
				i?.call(this, t), this.requestUpdate(e, a, n);
			},
			configurable: !0,
			enumerable: !0
		};
	}
	static getPropertyOptions(e) {
		return this.elementProperties.get(e) ?? se;
	}
	static _$Ei() {
		if (this.hasOwnProperty(f("elementProperties"))) return;
		let e = re(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(f("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(f("properties"))) {
			let e = this.properties, t = [...te(e), ...ne(e)];
			for (let n of t) this.createProperty(n, e[n]);
		}
		let e = this[Symbol.metadata];
		if (e !== null) {
			let t = litPropertyMetadata.get(e);
			if (t !== void 0) for (let [e, n] of t) this.elementProperties.set(e, n);
		}
		this._$Eh = /* @__PURE__ */ new Map();
		for (let [e, t] of this.elementProperties) {
			let n = this._$Eu(e, t);
			n !== void 0 && this._$Eh.set(n, e);
		}
		this.elementStyles = this.finalizeStyles(this.styles);
	}
	static finalizeStyles(e) {
		let t = [];
		if (Array.isArray(e)) {
			let n = new Set(e.flat(1 / 0).reverse());
			for (let e of n) t.unshift(c(e));
		} else e !== void 0 && t.push(c(e));
		return t;
	}
	static _$Eu(e, t) {
		let n = t.attribute;
		return !1 === n ? void 0 : typeof n == "string" ? n : typeof e == "string" ? e.toLowerCase() : void 0;
	}
	constructor() {
		super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
	}
	_$Ev() {
		this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
	}
	addController(e) {
		(this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
	}
	removeController(e) {
		this._$EO?.delete(e);
	}
	_$E_() {
		let e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
		for (let n of t.keys()) this.hasOwnProperty(n) && (e.set(n, this[n]), delete this[n]);
		e.size > 0 && (this._$Ep = e);
	}
	createRenderRoot() {
		let e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
		return s(e, this.constructor.elementStyles), e;
	}
	connectedCallback() {
		this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
	}
	enableUpdating(e) {}
	disconnectedCallback() {
		this._$EO?.forEach((e) => e.hostDisconnected?.());
	}
	attributeChangedCallback(e, t, n) {
		this._$AK(e, n);
	}
	_$ET(e, t) {
		let n = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, n);
		if (r !== void 0 && !0 === n.reflect) {
			let i = (n.converter?.toAttribute === void 0 ? p : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? p : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? m)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
			this.C(e, t, n);
		}
		!1 === this.isUpdatePending && (this._$ES = this._$EP());
	}
	C(e, t, { useDefault: n, reflect: r, wrapped: i }, a) {
		n && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), !0 !== i || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || n || (t = void 0), this._$AL.set(e, t)), !0 === r && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
	}
	async _$EP() {
		this.isUpdatePending = !0;
		try {
			await this._$ES;
		} catch (e) {
			Promise.reject(e);
		}
		let e = this.scheduleUpdate();
		return e != null && await e, !this.isUpdatePending;
	}
	scheduleUpdate() {
		return this.performUpdate();
	}
	performUpdate() {
		if (!this.isUpdatePending) return;
		if (!this.hasUpdated) {
			if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
				for (let [e, t] of this._$Ep) this[e] = t;
				this._$Ep = void 0;
			}
			let e = this.constructor.elementProperties;
			if (e.size > 0) for (let [t, n] of e) {
				let { wrapped: e } = n, r = this[t];
				!0 !== e || this._$AL.has(t) || r === void 0 || this.C(t, void 0, n, r);
			}
		}
		let e = !1, t = this._$AL;
		try {
			e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((e) => e.hostUpdate?.()), this.update(t)) : this._$EM();
		} catch (t) {
			throw e = !1, this._$EM(), t;
		}
		e && this._$AE(t);
	}
	willUpdate(e) {}
	_$AE(e) {
		this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
	}
	_$EM() {
		this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
	}
	get updateComplete() {
		return this.getUpdateComplete();
	}
	getUpdateComplete() {
		return this._$ES;
	}
	shouldUpdate(e) {
		return !0;
	}
	update(e) {
		this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
	}
	updated(e) {}
	firstUpdated(e) {}
};
h.elementStyles = [], h.shadowRootOptions = { mode: "open" }, h[f("elementProperties")] = /* @__PURE__ */ new Map(), h[f("finalized")] = /* @__PURE__ */ new Map(), oe?.({ ReactiveElement: h }), (d.reactiveElementVersions ??= []).push("2.1.2");
// node_modules/lit-html/lit-html.js
var ce = globalThis, le = (e) => e, g = ce.trustedTypes, ue = g ? g.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, de = "$lit$", _ = `lit$${Math.random().toFixed(9).slice(2)}$`, fe = "?" + _, pe = `<${fe}>`, v = document, y = () => v.createComment(""), b = (e) => e === null || typeof e != "object" && typeof e != "function", x = Array.isArray, me = (e) => x(e) || typeof e?.[Symbol.iterator] == "function", he = "[ 	\n\f\r]", S = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ge = /-->/g, _e = />/g, C = RegExp(`>|${he}(?:([^\\s"'>=/]+)(${he}*=${he}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), ve = /'/g, ye = /"/g, be = /^(?:script|style|textarea|title)$/i, xe = (e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}), w = xe(1), Se = xe(2), T = Symbol.for("lit-noChange"), E = Symbol.for("lit-nothing"), Ce = /* @__PURE__ */ new WeakMap(), D = v.createTreeWalker(v, 129);
function we(e, t) {
	if (!x(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return ue === void 0 ? t : ue.createHTML(t);
}
var Te = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = S;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === S ? c[1] === "!--" ? o = ge : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = C) : (be.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = C) : o = _e : o === C ? c[0] === ">" ? (o = i ?? S, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? C : c[3] === "\"" ? ye : ve) : o === ye || o === ve ? o = C : o === ge || o === _e ? o = S : (o = C, i = void 0);
		let ee = o === C && e[t + 1].startsWith("/>") ? " " : "";
		a += o === S ? n + pe : l >= 0 ? (r.push(s), n.slice(0, l) + de + n.slice(l) + _ + ee) : n + _ + (l === -2 ? t : ee);
	}
	return [we(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, O = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = Te(t, n);
		if (this.el = e.createElement(l, r), D.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = D.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(de)) {
					let t = u[o++], n = i.getAttribute(e).split(_), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? Oe : r[1] === "?" ? ke : r[1] === "@" ? Ae : A
					}), i.removeAttribute(e);
				} else e.startsWith(_) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (be.test(i.tagName)) {
					let e = i.textContent.split(_), t = e.length - 1;
					if (t > 0) {
						i.textContent = g ? g.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], y()), D.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], y());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === fe) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(_, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += _.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = v.createElement("template");
		return n.innerHTML = e, n;
	}
};
function k(e, t, n = e, r) {
	if (t === T) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = b(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = k(e, i._$AS(e, t.values), i, r)), t;
}
var Ee = class {
	constructor(e, t) {
		this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
	}
	get parentNode() {
		return this._$AM.parentNode;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	u(e) {
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? v).importNode(t, !0);
		D.currentNode = r;
		let i = D.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new De(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new je(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = D.nextNode(), a++);
		}
		return D.currentNode = v, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, De = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = E, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
	}
	get parentNode() {
		let e = this._$AA.parentNode, t = this._$AM;
		return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
	}
	get startNode() {
		return this._$AA;
	}
	get endNode() {
		return this._$AB;
	}
	_$AI(e, t = this) {
		e = k(this, e, t), b(e) ? e === E || e == null || e === "" ? (this._$AH !== E && this._$AR(), this._$AH = E) : e !== this._$AH && e !== T && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? me(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== E && b(this._$AH) ? this._$AA.nextSibling.data = e : this.T(v.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = O.createElement(we(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new Ee(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = Ce.get(e.strings);
		return t === void 0 && Ce.set(e.strings, t = new O(e)), t;
	}
	k(t) {
		x(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(y()), this.O(y()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = le(e).nextSibling;
			le(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, A = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = E, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = E;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = k(this, e, t, 0), a = !b(e) || e !== this._$AH && e !== T, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = k(this, r[n + o], t, o), s === T && (s = this._$AH[o]), a ||= !b(s) || s !== this._$AH[o], s === E ? e = E : e !== E && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === E ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, Oe = class extends A {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === E ? void 0 : e;
	}
}, ke = class extends A {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== E);
	}
}, Ae = class extends A {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = k(this, e, t, 0) ?? E) === T) return;
		let n = this._$AH, r = e === E && n !== E || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== E && (n === E || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, je = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		k(this, e);
	}
}, Me = ce.litHtmlPolyfillSupport;
Me?.(O, De), (ce.litHtmlVersions ??= []).push("3.3.3");
var Ne = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new De(t.insertBefore(y(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, Pe = globalThis, j = class extends h {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Ne(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return T;
	}
};
j._$litElement$ = !0, j.finalized = !0, Pe.litElementHydrateSupport?.({ LitElement: j });
var Fe = Pe.litElementPolyfillSupport;
Fe?.({ LitElement: j }), (Pe.litElementVersions ??= []).push("4.2.2");
// node_modules/@lit/reactive-element/decorators/custom-element.js
var M = (e) => (t, n) => {
	n === void 0 ? customElements.define(e, t) : n.addInitializer(() => {
		customElements.define(e, t);
	});
}, Ie = {
	attribute: !0,
	type: String,
	converter: p,
	reflect: !1,
	hasChanged: m
}, Le = (e = Ie, t, n) => {
	let { kind: r, metadata: i } = n, a = globalThis.litPropertyMetadata.get(i);
	if (a === void 0 && globalThis.litPropertyMetadata.set(i, a = /* @__PURE__ */ new Map()), r === "setter" && ((e = Object.create(e)).wrapped = !0), a.set(n.name, e), r === "accessor") {
		let { name: r } = n;
		return {
			set(n) {
				let i = t.get.call(this);
				t.set.call(this, n), this.requestUpdate(r, i, e, !0, n);
			},
			init(t) {
				return t !== void 0 && this.C(r, void 0, e, t), t;
			}
		};
	}
	if (r === "setter") {
		let { name: r } = n;
		return function(n) {
			let i = this[r];
			t.call(this, n), this.requestUpdate(r, i, e, !0, n);
		};
	}
	throw Error("Unsupported decorator location: " + r);
};
function N(e) {
	return (t, n) => typeof n == "object" ? Le(e, t, n) : ((e, t, n) => {
		let r = t.hasOwnProperty(n);
		return t.constructor.createProperty(n, e), r ? Object.getOwnPropertyDescriptor(t, n) : void 0;
	})(e, t, n);
}
// node_modules/@lit/reactive-element/decorators/state.js
function P(e) {
	return N({
		...e,
		state: !0,
		attribute: !1
	});
}
// node_modules/@lit/reactive-element/decorators/base.js
var Re = (e, t, n) => (n.configurable = !0, n.enumerable = !0, Reflect.decorate && typeof t != "object" && Object.defineProperty(e, t, n), n);
// node_modules/@lit/reactive-element/decorators/query.js
function F(e, t) {
	return (n, r, i) => {
		let a = (t) => t.renderRoot?.querySelector(e) ?? null;
		if (t) {
			let { get: e, set: t } = typeof r == "object" ? n : i ?? (() => {
				let e = Symbol();
				return {
					get() {
						return this[e];
					},
					set(t) {
						this[e] = t;
					}
				};
			})();
			return Re(n, r, { get() {
				let n = e.call(this);
				return n === void 0 && (n = a(this), (n !== null || this.hasUpdated) && t.call(this, n)), n;
			} });
		}
		return Re(n, r, { get() {
			return a(this);
		} });
	};
}
// src/api.ts
var ze = class {
	constructor(e) {
		this.hass = e;
	}
	call(e, t = {}) {
		return this.hass.connection.sendMessagePromise({
			type: `ban_guard/${e}`,
			...t
		});
	}
	overview() {
		return this.call("overview");
	}
	async bans() {
		return (await this.call("bans")).bans;
	}
	async ban(e, t, n) {
		return (await this.call("ban", {
			ip: e,
			reason: t,
			duration: n
		})).ban;
	}
	async unban(e) {
		return (await this.call("unban", { ips: e })).removed;
	}
	restore(e) {
		return this.call("restore", { bans: e });
	}
	async allowlist() {
		return (await this.call("allowlist")).allowlist;
	}
	async allow(e, t) {
		return (await this.call("allow", {
			value: e,
			comment: t
		})).entry;
	}
	async disallow(e) {
		return (await this.call("disallow", { value: e })).entry;
	}
	async activity(e) {
		return (await this.call("activity", e)).entries;
	}
	subscribeActivity(e) {
		return this.hass.connection.subscribeMessage((t) => e(t.entry), { type: "ban_guard/subscribe_activity" });
	}
	subscribeUpdates(e) {
		return this.hass.connection.subscribeMessage(() => e(), { type: "ban_guard/subscribe_updates" });
	}
	history(e) {
		return this.call("history", { ip: e });
	}
	exportBackup() {
		return this.call("export");
	}
	importBackup(e, t, n) {
		return this.call("import", {
			data: e,
			dry_run: t,
			include_settings: n
		});
	}
	settings() {
		return this.call("settings");
	}
	npmSync() {
		return this.call("npm_sync");
	}
};
function I(e, t) {
	let n = e, r = n?.translation_key ?? n?.code;
	if (r) {
		let e = t(`errors.${r}`, n?.translation_placeholders ?? {});
		if (e !== `errors.${r}`) return e;
	}
	return t("common.error", { message: n?.message ?? (e instanceof Error ? e.message : String(e)) });
}
// src/styles.ts
var L = o`
  :host {
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, inherit));
  }
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  ha-card,
  .card {
    display: block;
    background: var(--ha-card-background, var(--card-background-color, #fff));
    border-radius: var(--ha-card-border-radius, 12px);
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color));
    box-shadow: var(--ha-card-box-shadow, none);
    padding: 16px;
  }
  h2 {
    font-size: 1.1rem;
    font-weight: 500;
    margin: 0 0 12px;
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  .spacer {
    flex: 1;
  }
  button {
    font: inherit;
    cursor: pointer;
    border-radius: 18px;
    padding: 6px 14px;
    min-height: 36px;
    border: 1px solid var(--divider-color);
    background: transparent;
    color: var(--primary-color);
    font-weight: 500;
  }
  button.primary {
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
    border-color: var(--primary-color);
  }
  button.danger {
    color: var(--error-color);
    border-color: var(--error-color);
  }
  button.danger.primary {
    background: var(--error-color);
    color: var(--text-primary-color, #fff);
  }
  button.icon {
    border: none;
    padding: 6px;
    min-width: 36px;
    border-radius: 50%;
    color: var(--secondary-text-color);
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  button:focus-visible,
  input:focus-visible,
  select:focus-visible,
  textarea:focus-visible,
  [tabindex]:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }
  input,
  select,
  textarea {
    font: inherit;
    color: var(--primary-text-color);
    background: var(--input-fill-color, var(--secondary-background-color));
    border: 1px solid var(--input-idle-line-color, var(--divider-color));
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 40px;
    width: 100%;
  }
  label {
    display: block;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
    margin: 12px 0 4px;
  }
  .help {
    font-size: 0.8rem;
    color: var(--secondary-text-color);
    margin-top: 4px;
  }
  .error {
    color: var(--error-color);
    font-size: 0.85rem;
    margin-top: 4px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th,
  td {
    text-align: start;
    padding: 10px 8px;
    border-bottom: 1px solid var(--divider-color);
    vertical-align: middle;
  }
  th {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  th button {
    border: none;
    padding: 0;
    min-height: 0;
    color: inherit;
    font-weight: inherit;
    border-radius: 0;
  }
  tbody tr:hover {
    background: var(--secondary-background-color);
  }
  .mono {
    font-family: var(--ha-font-family-code, ui-monospace, monospace);
    font-size: 0.9em;
    word-break: break-all;
  }
  .chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75rem;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    white-space: nowrap;
  }
  .chip.warn {
    color: var(--warning-color);
  }
  .chip.bad {
    color: var(--error-color);
  }
  .chip.good {
    color: var(--success-color);
  }
  .empty {
    text-align: center;
    padding: 32px 16px;
  }
  .empty ha-icon {
    --mdc-icon-size: 48px;
    color: var(--secondary-text-color);
  }
  .empty h3 {
    margin: 8px 0;
    font-weight: 500;
  }
  .empty p {
    color: var(--secondary-text-color);
    max-width: 480px;
    margin: 0 auto 16px;
  }
  .banner {
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    border-inline-start: 4px solid var(--warning-color);
    background: var(--secondary-background-color);
  }
  .banner.bad {
    border-color: var(--error-color);
  }
  .table-wrap {
    overflow-x: auto;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  @media (max-width: 600px) {
    .hide-narrow {
      display: none;
    }
    th,
    td {
      padding: 8px 4px;
    }
  }
`;
// \0@oxc-project+runtime@0.156.0/helpers/esm/decorate.js
function R(e, t, n, r) {
	var i = arguments.length, a = i < 3 ? t : r === null ? r = Object.getOwnPropertyDescriptor(t, n) : r, o;
	if (typeof Reflect == "object" && typeof Reflect.decorate == "function") a = Reflect.decorate(e, t, n, r);
	else for (var s = e.length - 1; s >= 0; s--) (o = e[s]) && (a = (i < 3 ? o(a) : i > 3 ? o(t, n, a) : o(t, n)) || a);
	return i > 3 && a && Object.defineProperty(t, n, a), a;
}
// src/components/dialog.ts
var z = class extends j {
	constructor(...e) {
		super(...e), this.heading = "", this.open = !1, this.opener = null;
	}
	updated(e) {
		e.has("open") && (this.open && !this.dialog.open ? (this.opener = document.activeElement, this.dialog.showModal()) : !this.open && this.dialog.open && this.dialog.close());
	}
	onClose() {
		this.open && (this.open = !1, this.dispatchEvent(new CustomEvent("closed"))), this.opener?.focus?.();
	}
	render() {
		return w`<dialog aria-labelledby="h" @close=${this.onClose}>
      <h2 id="h">${this.heading}</h2>
      <div class="body"><slot></slot></div>
      <div class="actions"><slot name="actions"></slot></div>
    </dialog>`;
	}
	static {
		this.styles = [L, o`
      dialog {
        border: none;
        border-radius: var(--ha-dialog-border-radius, 24px);
        padding: 24px;
        width: min(560px, calc(100vw - 32px));
        max-height: calc(100vh - 32px);
        background: var(--mdc-theme-surface, var(--card-background-color));
        color: var(--primary-text-color);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      }
      dialog::backdrop {
        background: rgba(0, 0, 0, 0.4);
      }
      .actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 24px;
        flex-wrap: wrap;
      }
    `];
	}
};
R([N()], z.prototype, "heading", void 0), R([N({ type: Boolean })], z.prototype, "open", void 0), R([F("dialog")], z.prototype, "dialog", void 0), z = R([M("bg-dialog")], z);
var Be = class extends j {
	constructor(...e) {
		super(...e), this.options = null, this.resolve = null;
	}
	ask(e) {
		return this.resolve?.(!1), this.options = e, new Promise((e) => {
			this.resolve = e;
		});
	}
	finish(e) {
		this.resolve?.(e), this.resolve = null, this.options = null;
	}
	render() {
		let e = this.options;
		return w`<bg-dialog
      .open=${e !== null}
      .heading=${e?.title ?? ""}
      @closed=${() => this.finish(!1)}
    >
      ${e ? w`<p>${e.body}</p>` : E}
      <button slot="actions" @click=${() => this.finish(!1)}>${e?.cancel}</button>
      <button
        slot="actions"
        class=${e?.destructive ? "danger primary" : "primary"}
        @click=${() => this.finish(!0)}
      >
        ${e?.confirm}
      </button>
    </bg-dialog>`;
	}
	static {
		this.styles = [L];
	}
};
R([N({ attribute: !1 })], Be.prototype, "options", void 0), Be = R([M("bg-confirm")], Be);
// src/logic/enforcement.ts
function B(e, t) {
	if (!e || e.enforced && !e.partial) return {
		level: "ok",
		label: "",
		detail: ""
	};
	let n = e.reason ?? "unknown", r;
	if (n.startsWith("hook_")) r = t("enforcement.reasons.hook", { status: n.slice(5) });
	else {
		let i = `enforcement.reasons.${n}`, a = t(i, {
			protected: e.protected ?? "",
			exempt: e.exempt.join(", ")
		});
		r = a === i ? t("enforcement.reasons.unknown") : a;
	}
	return e.enforced ? {
		level: "partial",
		label: t("enforcement.partial"),
		detail: r
	} : {
		level: "off",
		label: t("enforcement.not_enforced"),
		detail: r
	};
}
function Ve(e) {
	return !!e.enforcement && (!e.enforcement.enforced || e.enforcement.partial);
}
// src/logic/format.ts
function V(e) {
	if (!e || !/^[A-Za-z]{2}$/.test(e)) return "";
	let t = 127462, n = e.toUpperCase();
	return String.fromCodePoint(t + n.charCodeAt(0) - 65, t + n.charCodeAt(1) - 65);
}
function He(e, t) {
	if (!e) return null;
	let n = Date.parse(e) - t;
	if (Number.isNaN(n)) return null;
	if (n <= 0) return {
		expired: !0,
		days: 0,
		hours: 0,
		minutes: 0,
		seconds: 0
	};
	let r = Math.floor(n / 1e3);
	return {
		expired: !1,
		days: Math.floor(r / 86400),
		hours: Math.floor(r % 86400 / 3600),
		minutes: Math.floor(r % 3600 / 60),
		seconds: r % 60
	};
}
function Ue(e) {
	return e.days > 0 ? `${e.days}d ${e.hours}h` : e.hours > 0 ? `${e.hours}h ${String(e.minutes).padStart(2, "0")}m` : `${e.minutes}m ${String(e.seconds).padStart(2, "0")}s`;
}
function H(e, t) {
	if (!e) return "";
	let n = new Date(e);
	return Number.isNaN(n.getTime()) ? e : new Intl.DateTimeFormat(t, {
		dateStyle: "medium",
		timeStyle: "short"
	}).format(n);
}
function We(e) {
	let t = Ge(Math.max(0, ...e));
	return {
		ratios: e.map((e) => t === 0 ? 0 : e / t),
		max: t
	};
}
function Ge(e) {
	if (e <= 0) return 0;
	let t = 10 ** Math.floor(Math.log10(e));
	for (let n of [
		1,
		2,
		2.5,
		5,
		10
	]) if (e <= n * t) return n * t;
	return 10 * t;
}
function Ke(e, t) {
	return `${e}-${t.toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;
}
// src/components/drawer.ts
var U = class extends j {
	constructor(...e) {
		super(...e), this.ip = null, this.revision = 0, this.data = null;
	}
	updated(e) {
		e.has("ip") ? (this.data = null, this.ip ? (this.dialog.open || this.dialog.showModal(), this.load()) : this.dialog.open && this.dialog.close()) : e.has("revision") && this.ip && this.load();
	}
	async load() {
		if (this.ip) try {
			this.data = await this.ctx.api.history(this.ip);
		} catch (e) {
			this.ctx.error(e), this.close();
		}
	}
	close() {
		this.ip = null, this.dispatchEvent(new CustomEvent("closed"));
	}
	async unban(e) {
		let { t } = this.ctx, n = this.data?.ip;
		if (n && await this.ctx.confirm({
			title: t("bans.confirm_unban_title", { count: 1 }),
			body: t("bans.confirm_unban_body", { list: n }),
			confirm: t(e ? "drawer.allowlist_it" : "bans.unban"),
			destructive: !0
		})) try {
			let r = await this.ctx.api.unban([n]);
			e && await this.ctx.api.allow(n, ""), this.ctx.toast({
				message: t("bans.unbanned", { count: 1 }),
				actionLabel: t("common.undo"),
				action: async () => {
					try {
						e && await this.ctx.api.disallow(n), await this.ctx.api.restore(r);
					} catch (e) {
						this.ctx.error(e);
					}
				}
			});
		} catch (e) {
			this.ctx.error(e);
		}
	}
	render() {
		let { t: e, language: t } = this.ctx, n = this.data;
		return w`<dialog aria-labelledby="dh" @close=${() => this.ip && this.close()}>
      <header class="row">
        <h2 id="dh" class="mono">${this.ip ?? ""}</h2>
        <span class="spacer"></span>
        <button class="icon" @click=${this.close} aria-label=${e("common.close")}>
          <ha-icon icon="mdi:close"></ha-icon>
        </button>
      </header>
      ${n ? w`<dl>
              <dt>${e("drawer.location")}</dt>
              <dd>
                ${n.geo ? `${V(n.geo.country)} ${[n.geo.city, n.geo.country_name ?? n.geo.country].filter(Boolean).join(", ")}` : e("common.unknown")}
              </dd>
              <dt>${e("drawer.hostname")}</dt>
              <dd class="mono">${n.hostname ?? e("drawer.rdns_off")}</dd>
              <dt>${e("drawer.offenses")}</dt>
              <dd>${n.offenses}</dd>
              <dt>${e("drawer.allowlisted")}</dt>
              <dd>${n.allowlisted ? e("common.yes") : e("common.no")}</dd>
              <dt>${e("drawer.ban")}</dt>
              <dd>
                ${n.ban ? w`${n.ban.reason || e(`bans.source_${n.ban.source}`)} ·
                    ${n.ban.expires_at ? H(n.ban.expires_at, t) : e("common.permanent")}` : e("common.none")}
              </dd>
              ${n.ban && B(n.ban.enforcement, e).level !== "ok" ? w`<dt>${e("drawer.enforcement")}</dt>
                    <dd class="warn-text">
                      ${B(n.ban.enforcement, e).label}:
                      ${B(n.ban.enforcement, e).detail}
                    </dd>` : E}
            </dl>
            ${n.ban ? w`<div class="row">
                  <button class="danger" @click=${() => this.unban(!1)}>
                    ${e("bans.unban")}
                  </button>
                  <button @click=${() => this.unban(!0)}>${e("drawer.allowlist_it")}</button>
                </div>` : E}
            <h2 class="history">${e("drawer.history")}</h2>
            ${n.activity.length ? w`<ol class="timeline">
                  ${n.activity.map((n) => w`<li>
                      <span class="chip">${e(`activity.types.${n.type}`)}</span>
                      <span class="muted">${H(n.ts, t)}</span>
                      ${n.path ? w`<div class="mono small">${n.path}</div>` : E}
                      ${n.detail ? w`<div class="small">${n.detail}</div>` : E}
                    </li>`)}
                </ol>` : w`<p class="muted">${e("drawer.no_history")}</p>`}` : w`<p class="muted">${e("common.loading")}</p>`}
    </dialog>`;
	}
	static {
		this.styles = [L, o`
      dialog {
        margin: 0 0 0 auto;
        height: 100vh;
        max-height: 100vh;
        width: min(440px, 100vw);
        border: none;
        padding: 16px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        box-shadow: -4px 0 24px rgba(0, 0, 0, 0.25);
      }
      dialog::backdrop {
        background: rgba(0, 0, 0, 0.3);
      }
      h2 {
        margin: 0;
      }
      dl {
        display: grid;
        grid-template-columns: max-content 1fr;
        gap: 8px 16px;
        margin: 16px 0;
      }
      dt {
        color: var(--secondary-text-color);
      }
      dd {
        margin: 0;
      }
      .history {
        margin-top: 24px;
      }
      .warn-text {
        color: var(--warning-color);
      }
      .timeline {
        list-style: none;
        padding: 0;
        margin: 8px 0 0;
      }
      .timeline li {
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .small {
        font-size: 0.8rem;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
    `];
	}
};
R([N({ attribute: !1 })], U.prototype, "ctx", void 0), R([N()], U.prototype, "ip", void 0), R([N({ type: Number })], U.prototype, "revision", void 0), R([P()], U.prototype, "data", void 0), R([F("dialog")], U.prototype, "dialog", void 0), U = R([M("bg-drawer")], U);
// src/components/toast.ts
var qe = class extends j {
	constructor(...e) {
		super(...e), this.current = null;
	}
	show(e) {
		window.clearTimeout(this.timer), this.current = e, this.timer = window.setTimeout(() => this.dismiss(), e.duration ?? 8e3);
	}
	dismiss() {
		window.clearTimeout(this.timer), this.current = null;
	}
	async run() {
		let e = this.current?.action;
		this.dismiss(), await e?.();
	}
	render() {
		let e = this.current;
		return w`<div class="region" role="status" aria-live="polite">
      ${e ? w`<div class="toast">
            <span>${e.message}</span>
            ${e.actionLabel ? w`<button class="action" @click=${this.run}>${e.actionLabel}</button>` : E}
          </div>` : E}
    </div>`;
	}
	static {
		this.styles = [L, o`
      .region {
        position: fixed;
        inset-inline: 0;
        bottom: 16px;
        display: flex;
        justify-content: center;
        pointer-events: none;
        z-index: 10;
      }
      .toast {
        pointer-events: auto;
        display: flex;
        align-items: center;
        gap: 16px;
        max-width: calc(100vw - 32px);
        padding: 8px 8px 8px 16px;
        border-radius: 8px;
        background: var(--sidebar-background-color, #323232);
        color: var(--sidebar-text-color, #fff);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
      }
      .action {
        border: none;
        color: var(--primary-color);
      }
    `];
	}
};
R([P()], qe.prototype, "current", void 0), qe = R([M("bg-toast")], qe);
var Je = {
	title: "Ban Guard",
	tabs: {
		overview: "Overview",
		bans: "Bans",
		allowlist: "Allowlist",
		activity: "Activity",
		settings: "Settings",
		backup: "Import & export"
	},
	common: {
		cancel: "Cancel",
		confirm: "Confirm",
		close: "Close",
		undo: "Undo",
		save: "Save",
		loading: "Loading…",
		retry: "Retry",
		error: "Something went wrong: {message}",
		search: "Search",
		permanent: "Permanent",
		expired: "Expired",
		never: "Never",
		none: "None",
		unknown: "Unknown",
		yes: "Yes",
		no: "No",
		details: "Details for {ip}",
		you: "you"
	},
	status: {
		hook_active: "Request protection active",
		hook_incompatible: "Request protection disabled: this Home Assistant version is not supported yet. Built-in banning still works.",
		hook_ip_ban_disabled: "Home Assistant's ip_ban_enabled is off, so bans are not enforced.",
		hook_error: "Request protection stopped after errors. Built-in banning still works. Reload Ban Guard to retry.",
		hook_other: "Request protection status: {status}",
		under_attack: "Under attack: failed logins are above the configured rate.",
		protection_off: "Automatic banning is off. Turn it on in Settings."
	},
	overview: {
		active_bans: "Active bans",
		bans_24h: "Bans (24 h)",
		blocked_24h: "Blocked requests (24 h)",
		allowlist: "Allowlisted entries",
		chart_title: "Failed logins, last 7 days",
		chart_label: "{date}: {count} failed logins",
		top_ips: "Top offending addresses",
		top_countries: "Top countries",
		no_offenders: "No failed logins or blocked requests in the last 7 days.",
		countries_need_geoip: "Turn on GeoIP in Settings to see countries.",
		last_ban: "Last ban",
		attempts: "{count} events",
		logins_24h: "Successful logins (24 h)",
		failed_24h: "Failed logins (24 h)"
	},
	bans: {
		add: "Ban address",
		add_title: "Ban an address or range",
		ip_label: "IP address or CIDR range",
		ip_help: "For example 203.0.113.7, 198.51.100.0/24 or 2001:db8::/32. Paste several, separated by spaces or new lines.",
		reason_label: "Reason (optional)",
		duration_label: "Duration",
		duration_help: "For example 30m, 24h, 7d or permanent.",
		invalid_ip: "{value} is not a valid IP address or CIDR range.",
		invalid_duration: "Use values like 30m, 24h, 7d or permanent.",
		col_ip: "Address",
		col_country: "Country",
		col_reason: "Reason",
		col_source: "Source",
		col_created: "Banned",
		col_expires: "Expires",
		select_all: "Select all visible bans",
		select_one: "Select {ip}",
		unban: "Unban",
		unban_selected: "Unban {count} selected",
		confirm_unban_title: "Unban {count} address(es)?",
		confirm_unban_body: "These addresses will be able to reach Home Assistant again: {list}",
		unbanned: "Unbanned {count} address(es).",
		banned: "Banned {ip}.",
		filter_source: "Source",
		filter_kind: "Type",
		kind_all: "All",
		kind_permanent: "Permanent",
		kind_temporary: "Temporary",
		kind_network: "Ranges",
		source_all: "All sources",
		source_manual: "Manual",
		source_automatic: "Automatic",
		source_imported: "Imported",
		source_service: "Action",
		source_home_assistant: "Home Assistant",
		empty_title: "No active bans",
		empty_body: "Nobody is banned right now. Ban an address manually, or let failed-login protection do it for you.",
		no_match: "No bans match these filters.",
		sort_by: "Sort by {column}",
		count: "{shown} of {total}",
		kind_unenforced: "Not fully enforced",
		unenforced_title: "Ban saved, but not enforced",
		unenforced_body: "Requests from this address are still allowed. Remove the ban, or keep it so it applies once the reason goes away?",
		unenforced_remove: "Remove ban",
		unenforced_keep: "Keep ban",
		partial_title: "Ban saved, with exceptions"
	},
	drawer: {
		title: "Address details",
		hostname: "Hostname",
		location: "Location",
		offenses: "Offences",
		allowlisted: "Allowlisted",
		ban: "Ban",
		history: "History",
		no_history: "No recorded activity for this address.",
		rdns_off: "Reverse DNS is off",
		allowlist_it: "Unban and allowlist",
		enforcement: "Enforcement"
	},
	allowlist: {
		add: "Add entry",
		add_title: "Add to allowlist",
		value_label: "IP address, CIDR range or hostname",
		value_help: "Hostnames are re-resolved periodically. Allowlisted addresses are never banned.",
		comment_label: "Comment (optional)",
		invalid: "{value} is not a valid IP address, CIDR range or hostname.",
		col_value: "Entry",
		col_comment: "Comment",
		col_resolved: "Resolves to",
		col_added: "Added",
		remove: "Remove",
		remove_label: "Remove {value} from the allowlist",
		confirm_remove_title: "Remove {value} from the allowlist?",
		confirm_remove_body: "This address can be banned again after repeated failed logins.",
		removed: "Removed {value} from the allowlist.",
		added: "Added {value} to the allowlist.",
		empty_title: "The allowlist is empty",
		empty_body: "Add the addresses you always want to reach Home Assistant from, such as your home network or VPN. Your current address is {ip}.",
		add_current: "Add my current address",
		unresolved: "Not resolved yet"
	},
	activity: {
		live: "Live",
		paused: "Paused",
		pause: "Pause live updates",
		resume: "Resume live updates",
		filter: "Event type",
		all: "All events",
		load_more: "Load older entries",
		empty_title: "No activity yet",
		empty_body: "Sign-ins, failed logins, bans and blocked requests will appear here as they happen.",
		col_time: "Time",
		col_type: "Event",
		col_ip: "Address",
		col_path: "Path",
		col_details: "Details",
		types: {
			login: "Successful login",
			failed_login: "Failed login",
			allowlisted_failure: "Failed login (allowlisted)",
			ban: "Banned",
			unban: "Unbanned",
			expired: "Ban expired",
			blocked: "Blocked request",
			allow: "Allowlisted",
			disallow: "Removed from allowlist",
			refused: "Ban refused"
		}
	},
	settings: {
		intro: "All settings are edited in the integration's options. The shortcuts open the right page.",
		open_options: "Open Ban Guard options",
		protection: "Failed-login protection",
		protection_value: "{threshold} failures in {window} min → {ladder}",
		off: "Off",
		on: "On",
		notifications: "Notifications",
		logging: "Activity log",
		logging_value: "{days} days, up to {entries} entries",
		geoip: "GeoIP",
		rdns: "Reverse DNS",
		doh: "DNS-over-HTTPS",
		countries: "Country rules",
		countries_value: "Allow: {allow} · Block: {deny}",
		npm: "Nginx Proxy Manager",
		npm_detected: "Detected add-on: {name}",
		npm_sync: "Sync now",
		npm_synced: "Synced {count} bans to Nginx Proxy Manager.",
		npm_failed: "Sync failed: {error}",
		your_ip: "Your current address: {ip} (protected from bans)",
		privacy: "Outbound calls",
		privacy_none: "None. Ban Guard is not contacting any external service.",
		geoip_loaded: "Loaded ({edition})",
		geoip_loading: "Enabled, not loaded yet",
		geoip_error: "Error: {error}",
		logins: "Successful-login log",
		sessions: "Close open sessions on ban"
	},
	backup: {
		export_title: "Export",
		export_body: "Download a JSON backup of bans, allowlist and settings. Stored credentials are never included.",
		export: "Download backup",
		import_title: "Import",
		import_body: "Choose a Ban Guard backup. You will see what changes before anything is applied.",
		choose_file: "Choose backup file",
		invalid_json: "The file is not valid JSON.",
		not_backup: "This file is not a Ban Guard backup.",
		preview_title: "Import preview",
		new_bans: "New bans: {count}",
		existing_bans: "Already banned: {count}",
		expired_bans: "Expired (skipped): {count}",
		new_allow: "New allowlist entries: {count}",
		existing_allow: "Already allowlisted: {count}",
		errors: "Problems (skipped): {count}",
		settings_changes: "Settings that would change: {count}",
		include_settings: "Also import settings",
		apply: "Import",
		applied: "Import complete.",
		nothing: "Nothing to import."
	},
	errors: {
		protected_current: "Refused: {ip} would cover your current address {protected}.",
		protected_loopback: "Refused: {ip} would cover the loopback range {protected}.",
		protected_host: "Refused: {ip} would cover this Home Assistant host ({protected}).",
		protected_supervisor: "Refused: {ip} would cover the Supervisor network {protected}.",
		protected_proxy: "Refused: {ip} would cover the trusted proxy {protected}.",
		protected_admin: "Refused: {ip} would cover {protected}, used by an administrator in the last day.",
		protected_unspecified: "Refused: {ip} would cover {protected}.",
		allowlisted: "{ip} is on the allowlist. Remove it from the allowlist first.",
		invalid_ip: "{ip} is not a valid IP address or CIDR range.",
		invalid_allow: "{value} is not a valid IP address, CIDR range or hostname.",
		invalid_duration: "{value} is not a valid duration.",
		not_banned: "{ip} is not banned.",
		not_allowlisted: "{value} is not on the allowlist.",
		import_invalid_format: "This is not a Ban Guard backup.",
		import_unsupported_version: "This backup was made by a newer version of Ban Guard.",
		import_too_large: "The backup has more than {limit} items.",
		not_loaded: "Ban Guard is not loaded.",
		unauthorized: "Only administrators can use Ban Guard.",
		invalid: "Invalid entry: {detail}"
	},
	enforcement: {
		not_enforced: "Not enforced",
		partial: "Partly exempt",
		reasons: {
			allowlisted: "The address is on the allowlist.",
			protected_admin: "An administrator used {protected} in the last day, so it is never blocked.",
			protected_host: "{protected} is this Home Assistant host's own address.",
			protected_loopback: "{protected} is a loopback address.",
			protected_unspecified: "{protected} can never be blocked.",
			protected_supervisor: "{protected} is the Supervisor network.",
			protected_proxy: "{protected} is a trusted proxy.",
			protected_current: "{protected} is your current address.",
			partial: "Not applied to {exempt} (protected or allowlisted).",
			hook: "Request protection is not active ({status}).",
			unknown: "Ban Guard cannot apply this ban right now."
		}
	}
}, Ye = { en: Je };
function Xe(e, t) {
	let n = e;
	for (let e of t.split(".")) {
		if (n === void 0 || typeof n == "string") return;
		n = n[e];
	}
	return typeof n == "string" ? n : void 0;
}
function Ze(e) {
	if (!e) return "en";
	if (e in Ye) return e;
	let t = e.split("-")[0] ?? "en";
	return t in Ye ? t : "en";
}
function Qe(e) {
	let t = Ye[Ze(e)] ?? Je;
	return (e, n) => {
		let r = Xe(t, e) ?? Xe(Je, e) ?? e;
		return n ? r.replace(/\{(\w+)\}/g, (e, t) => t in n ? String(n[t]) : e) : r;
	};
}
// src/views/activity.ts
var $e = [
	"login",
	"failed_login",
	"allowlisted_failure",
	"ban",
	"unban",
	"expired",
	"blocked",
	"allow",
	"disallow",
	"refused"
], W = 100, et = 1e3, tt = {
	login: "good",
	failed_login: "warn",
	allowlisted_failure: "warn",
	ban: "bad",
	blocked: "bad",
	refused: "bad",
	unban: "good",
	allow: "good"
}, G = class extends j {
	constructor(...e) {
		super(...e), this.entries = null, this.filter = "all", this.live = !0, this.more = !0, this.unsub = null, this.buffered = [];
	}
	connectedCallback() {
		super.connectedCallback(), this.ctx && this.start();
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this.unsub?.(), this.unsub = null;
	}
	firstUpdated() {
		this.unsub || this.start();
	}
	async start() {
		if (await this.load(), !this.unsub) try {
			this.unsub = await this.ctx.api.subscribeActivity((e) => this.onEntry(e));
		} catch (e) {
			this.ctx.error(e);
		}
	}
	onEntry(e) {
		this.live ? (this.filter === "all" || e.type === this.filter) && (this.entries = [e, ...this.entries ?? []].slice(0, et)) : this.buffered.push(e);
	}
	types() {
		return this.filter === "all" ? void 0 : [this.filter];
	}
	async load() {
		try {
			let e = await this.ctx.api.activity({
				limit: W,
				types: this.types()
			});
			this.entries = e, this.more = e.length === W;
		} catch (e) {
			this.ctx.error(e);
		}
	}
	async loadMore() {
		let e = this.entries?.[this.entries.length - 1];
		if (e) try {
			let t = await this.ctx.api.activity({
				limit: W,
				before_id: e.id,
				types: this.types()
			});
			this.entries = [...this.entries ?? [], ...t], this.more = t.length === W;
		} catch (e) {
			this.ctx.error(e);
		}
	}
	toggleLive() {
		if (this.live = !this.live, this.live && this.buffered.length) {
			let e = this.buffered.filter((e) => this.filter === "all" || e.type === this.filter).reverse();
			this.entries = [...e, ...this.entries ?? []].slice(0, et), this.buffered = [];
		}
	}
	render() {
		let { t: e, language: t } = this.ctx, n = w`<div class="row toolbar">
      <select
        aria-label=${e("activity.filter")}
        @change=${(e) => {
			this.filter = e.target.value, this.load();
		}}
      >
        <option value="all">${e("activity.all")}</option>
        ${$e.map((t) => w`<option value=${t} ?selected=${this.filter === t}>
              ${e(`activity.types.${t}`)}
            </option>`)}
      </select>
      <span class="spacer"></span>
      <span class="chip ${this.live ? "good" : ""}" aria-live="polite">
        ${this.live ? e("activity.live") : e("activity.paused")}
      </span>
      <button
        class="icon"
        @click=${this.toggleLive}
        aria-label=${this.live ? e("activity.pause") : e("activity.resume")}
        aria-pressed=${!this.live}
        title=${this.live ? e("activity.pause") : e("activity.resume")}
      >
        <ha-icon icon=${this.live ? "mdi:pause" : "mdi:play"}></ha-icon>
      </button>
    </div>`;
		return this.entries === null ? w`<p class="muted">${e("common.loading")}</p>` : this.entries.length ? w`<ha-card>
      ${n}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>${e("activity.col_time")}</th>
              <th>${e("activity.col_type")}</th>
              <th>${e("activity.col_ip")}</th>
              <th class="hide-narrow">${e("activity.col_path")}</th>
              <th class="hide-narrow">${e("activity.col_details")}</th>
            </tr>
          </thead>
          <tbody>
            ${this.entries.map((n) => w`<tr>
                <td class="time">${H(n.ts, t)}</td>
                <td>
                  <span class="chip ${tt[n.type] ?? ""}">${e(`activity.types.${n.type}`)}</span>
                </td>
                <td>
                  <button
                    class="link mono"
                    @click=${() => this.ctx.openDetails(n.ip)}
                    aria-label=${e("common.details", { ip: n.ip })}
                  >
                    ${n.country ? `${V(n.country)} ` : ""}${n.ip}
                  </button>
                </td>
                <td class="hide-narrow mono">${n.path ?? ""}</td>
                <td class="hide-narrow details">
                  ${[
			n.detail,
			n.user,
			n.user_agent
		].filter(Boolean).join(" · ")}
                </td>
              </tr>`)}
          </tbody>
        </table>
      </div>
      ${this.more ? w`<div class="row more">
            <button @click=${this.loadMore}>${e("activity.load_more")}</button>
          </div>` : E}
    </ha-card>` : w`<ha-card>
        ${n}
        <div class="empty">
          <ha-icon icon="mdi:timeline-clock-outline" aria-hidden="true"></ha-icon>
          <h3>${e("activity.empty_title")}</h3>
          <p>${e("activity.empty_body")}</p>
        </div>
      </ha-card>`;
	}
	static {
		this.styles = [L, o`
      .toolbar {
        margin-bottom: 8px;
      }
      select {
        width: auto;
      }
      .time {
        white-space: nowrap;
        font-size: 0.85rem;
      }
      .details {
        max-width: 320px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.85rem;
        color: var(--secondary-text-color);
      }
      .link {
        border: none;
        padding: 0;
        min-height: 0;
        border-radius: 0;
        text-align: start;
      }
      .more {
        justify-content: center;
        margin-top: 12px;
      }
    `];
	}
};
R([N({ attribute: !1 })], G.prototype, "ctx", void 0), R([P()], G.prototype, "entries", void 0), R([P()], G.prototype, "filter", void 0), R([P()], G.prototype, "live", void 0), R([P()], G.prototype, "more", void 0), G = R([M("bg-activity")], G);
// src/logic/ip.ts
var nt = "(25[0-5]|2[0-4]\\d|1\\d\\d|[1-9]?\\d)", rt = RegExp(`^${nt}(\\.${nt}){3}$`), it = /^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))*\.?$/i;
function at(e) {
	return rt.test(e);
}
function ot(e) {
	let t = e.split("%")[0] ?? "";
	if (!/^[0-9a-f:.]+$/i.test(t) || !t.includes(":") || t.includes(":::") || /^:[^:]/.test(t) || /[^:]:$/.test(t)) return !1;
	let n = t.split("::").length - 1;
	if (n > 1) return !1;
	let r = t.split(":"), i = r[r.length - 1] ?? "", a = 8;
	if (i.includes(".")) {
		if (!at(i)) return !1;
		r = r.slice(0, -1), a = 6;
	}
	if (n === 0) return r.length === a && r.every((e) => /^[0-9a-f]{1,4}$/i.test(e));
	let o = r.filter((e) => e !== "");
	return o.length < a && o.every((e) => /^[0-9a-f]{1,4}$/i.test(e));
}
function st(e) {
	return at(e) || ot(e);
}
function ct(e) {
	let [t, n, ...r] = e.split("/");
	if (r.length || t === void 0 || n === void 0 || !/^\d{1,3}$/.test(n)) return !1;
	let i = Number(n);
	return at(t) ? i <= 32 : ot(t) ? i <= 128 : !1;
}
function lt(e) {
	let t = e.trim();
	return st(t) || ct(t);
}
function ut(e) {
	let t = e.trim();
	return it.test(t) && !st(t) && /[a-z]/i.test(t);
}
function dt(e) {
	return lt(e) || ut(e);
}
function ft(e) {
	return [...new Set(e.split(/[\s,;]+/).map((e) => e.trim()).filter(Boolean))];
}
var pt = /^(\d+)\s*([smhdw])$/i;
function mt(e) {
	let t = e.trim().toLowerCase();
	if ([
		"permanent",
		"perm",
		"forever",
		"never",
		"0"
	].includes(t)) return !0;
	let n = pt.exec(t);
	return n !== null && Number(n[1]) > 0;
}
// src/views/allowlist.ts
var K = class extends j {
	constructor(...e) {
		super(...e), this.revision = 0, this.requesterIp = null, this.entries = null, this.adding = !1, this.value = "", this.comment = "", this.formError = "", this.busy = !1;
	}
	updated(e) {
		(e.has("revision") || e.has("ctx")) && this.load();
	}
	async load() {
		try {
			this.entries = await this.ctx.api.allowlist();
		} catch (e) {
			this.ctx.error(e);
		}
	}
	openAdd(e = "") {
		this.value = e, this.comment = "", this.formError = "", this.adding = !0;
	}
	async submit(e) {
		e.preventDefault();
		let { t } = this.ctx, n = this.value.trim();
		if (!dt(n)) this.formError = t("allowlist.invalid", { value: n });
		else {
			this.busy = !0;
			try {
				let e = await this.ctx.api.allow(n, this.comment);
				this.adding = !1, this.ctx.toast({
					message: t("allowlist.added", { value: e.value }),
					actionLabel: t("common.undo"),
					action: async () => {
						try {
							await this.ctx.api.disallow(e.value);
						} catch (e) {
							this.ctx.error(e);
						}
					}
				});
			} catch (e) {
				this.formError = I(e, t);
			} finally {
				this.busy = !1;
			}
		}
	}
	async removeEntry(e) {
		let { t } = this.ctx;
		if (await this.ctx.confirm({
			title: t("allowlist.confirm_remove_title", { value: e.value }),
			body: t("allowlist.confirm_remove_body"),
			confirm: t("allowlist.remove"),
			destructive: !0
		})) try {
			await this.ctx.api.disallow(e.value), this.ctx.toast({
				message: t("allowlist.removed", { value: e.value }),
				actionLabel: t("common.undo"),
				action: async () => {
					try {
						await this.ctx.api.allow(e.value, e.comment);
					} catch (e) {
						this.ctx.error(e);
					}
				}
			});
		} catch (e) {
			this.ctx.error(e);
		}
	}
	dialog() {
		let { t: e } = this.ctx;
		return w`<bg-dialog
      .open=${this.adding}
      .heading=${e("allowlist.add_title")}
      @closed=${() => this.adding = !1}
    >
      <form id="allow-form" @submit=${this.submit}>
        <label for="value">${e("allowlist.value_label")}</label>
        <input
          id="value"
          required
          aria-describedby="value-help"
          .value=${this.value}
          @input=${(e) => this.value = e.target.value}
        />
        <div class="help" id="value-help">${e("allowlist.value_help")}</div>
        <label for="comment">${e("allowlist.comment_label")}</label>
        <input
          id="comment"
          maxlength="200"
          .value=${this.comment}
          @input=${(e) => this.comment = e.target.value}
        />
        ${this.formError ? w`<div class="error" role="alert">${this.formError}</div>` : E}
      </form>
      <button slot="actions" @click=${() => this.adding = !1}>${e("common.cancel")}</button>
      <button slot="actions" class="primary" type="submit" form="allow-form" ?disabled=${this.busy}>
        ${e("allowlist.add")}
      </button>
    </bg-dialog>`;
	}
	render() {
		let { t: e, language: t } = this.ctx;
		return this.entries === null ? w`<p class="muted">${e("common.loading")}</p>` : this.entries.length ? w`<ha-card>
        <div class="row toolbar">
          <span class="spacer"></span>
          <button class="primary" @click=${() => this.openAdd()}>${e("allowlist.add")}</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>${e("allowlist.col_value")}</th>
                <th>${e("allowlist.col_comment")}</th>
                <th class="hide-narrow">${e("allowlist.col_resolved")}</th>
                <th class="hide-narrow">${e("allowlist.col_added")}</th>
                <th><span class="sr-only">${e("allowlist.remove")}</span></th>
              </tr>
            </thead>
            <tbody>
              ${this.entries.map((n) => w`<tr>
                  <td class="mono">${n.value}</td>
                  <td>${n.comment}</td>
                  <td class="hide-narrow mono">
                    ${n.hostname ? n.resolved.length ? n.resolved.join(", ") : w`<span class="muted">${e("allowlist.unresolved")}</span>` : ""}
                  </td>
                  <td class="hide-narrow">${H(n.created_at, t)}</td>
                  <td>
                    <button
                      class="icon"
                      @click=${() => this.removeEntry(n)}
                      aria-label=${e("allowlist.remove_label", { value: n.value })}
                      title=${e("allowlist.remove")}
                    >
                      <ha-icon icon="mdi:delete-outline"></ha-icon>
                    </button>
                  </td>
                </tr>`)}
            </tbody>
          </table>
        </div>
      </ha-card>
      ${this.dialog()}` : w`<ha-card class="empty">
          <ha-icon icon="mdi:playlist-check" aria-hidden="true"></ha-icon>
          <h3>${e("allowlist.empty_title")}</h3>
          <p>${e("allowlist.empty_body", { ip: this.requesterIp ?? e("common.unknown") })}</p>
          <div class="row" style="justify-content:center">
            ${this.requesterIp ? w`<button @click=${() => this.openAdd(this.requesterIp ?? "")}>
                  ${e("allowlist.add_current")}
                </button>` : E}
            <button class="primary" @click=${() => this.openAdd()}>${e("allowlist.add")}</button>
          </div>
        </ha-card>
        ${this.dialog()}`;
	}
	static {
		this.styles = [L, o`
      .toolbar {
        margin-bottom: 8px;
      }
    `];
	}
};
R([N({ attribute: !1 })], K.prototype, "ctx", void 0), R([N({ type: Number })], K.prototype, "revision", void 0), R([N()], K.prototype, "requesterIp", void 0), R([P()], K.prototype, "entries", void 0), R([P()], K.prototype, "adding", void 0), R([P()], K.prototype, "value", void 0), R([P()], K.prototype, "comment", void 0), R([P()], K.prototype, "formError", void 0), R([P()], K.prototype, "busy", void 0), K = R([M("bg-allowlist")], K);
// src/logic/backup.ts
function ht(e) {
	let t;
	try {
		t = JSON.parse(e);
	} catch {
		return {
			ok: !1,
			error: "invalid_json"
		};
	}
	return typeof t != "object" || !t || Array.isArray(t) || t.format !== "ban_guard" ? {
		ok: !1,
		error: "not_backup"
	} : {
		ok: !0,
		data: t
	};
}
// src/views/backup.ts
var q = class extends j {
	constructor(...e) {
		super(...e), this.data = null, this.preview = null, this.includeSettings = !1, this.error = "", this.busy = !1;
	}
	async exportBackup() {
		try {
			let e = await this.ctx.api.exportBackup(), t = new Blob([JSON.stringify(e, null, 2)], { type: "application/json" }), n = URL.createObjectURL(t), r = document.createElement("a");
			r.href = n, r.download = Ke("ban_guard", /* @__PURE__ */ new Date()), r.click(), URL.revokeObjectURL(n);
		} catch (e) {
			this.ctx.error(e);
		}
	}
	async onFile(e) {
		let { t } = this.ctx, n = e.target.files?.[0];
		if (this.preview = null, this.error = "", !n) return;
		let r = ht(await n.text());
		if (!r.ok) this.error = t(`backup.${r.error}`);
		else {
			this.data = r.data;
			try {
				this.preview = (await this.ctx.api.importBackup(r.data, !0, !1)).preview;
			} catch (e) {
				this.error = I(e, t);
			}
		}
	}
	async apply() {
		let { t: e } = this.ctx;
		this.busy = !0;
		try {
			await this.ctx.api.importBackup(this.data, !1, this.includeSettings), this.ctx.toast({ message: e("backup.applied") }), this.preview = null, this.data = null;
		} catch (t) {
			this.error = I(t, e);
		} finally {
			this.busy = !1;
		}
	}
	renderPreview(e) {
		let { t } = this.ctx, n = Object.keys(e.settings).length, r = !e.bans_new.length && !e.allow_new.length && !(this.includeSettings && n);
		return w`<section aria-labelledby="preview-h" class="preview">
      <h2 id="preview-h">${t("backup.preview_title")}</h2>
      <ul>
        <li>${t("backup.new_bans", { count: e.bans_new.length })}</li>
        <li class="muted">${t("backup.existing_bans", { count: e.bans_existing.length })}</li>
        <li class="muted">${t("backup.expired_bans", { count: e.bans_expired.length })}</li>
        <li>${t("backup.new_allow", { count: e.allow_new.length })}</li>
        <li class="muted">${t("backup.existing_allow", { count: e.allow_existing.length })}</li>
        <li>${t("backup.settings_changes", { count: n })}</li>
        ${e.errors.length ? w`<li class="error">${t("backup.errors", { count: e.errors.length })}
              <ul>
                ${e.errors.slice(0, 20).map((e) => w`<li>${e.section} #${e.index ?? "-"}: ${t(`errors.${e.error}`, Object.fromEntries(Object.entries(e).map(([e, t]) => [e, String(t)])))}</li>`)}
              </ul>
            </li>` : E}
      </ul>
      ${n ? w`<label class="check">
            <input
              type="checkbox"
              .checked=${this.includeSettings}
              @change=${(e) => this.includeSettings = e.target.checked}
            />
            ${t("backup.include_settings")}
          </label>` : E}
      <div class="row">
        <button class="primary" ?disabled=${this.busy || r} @click=${this.apply}>
          ${t("backup.apply")}
        </button>
        ${r ? w`<span class="muted">${t("backup.nothing")}</span>` : E}
      </div>
    </section>`;
	}
	render() {
		let { t: e } = this.ctx;
		return w`<div class="grid">
      <ha-card>
        <h2>${e("backup.export_title")}</h2>
        <p class="muted">${e("backup.export_body")}</p>
        <button class="primary" @click=${this.exportBackup}>
          <ha-icon icon="mdi:download"></ha-icon> ${e("backup.export")}
        </button>
      </ha-card>
      <ha-card>
        <h2>${e("backup.import_title")}</h2>
        <p class="muted">${e("backup.import_body")}</p>
        <label for="file">${e("backup.choose_file")}</label>
        <input id="file" type="file" accept="application/json,.json" @change=${this.onFile} />
        ${this.error ? w`<div class="error" role="alert">${this.error}</div>` : E}
        ${this.preview ? this.renderPreview(this.preview) : E}
      </ha-card>
    </div>`;
	}
	static {
		this.styles = [L, o`
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 12px;
      }
      .check {
        display: flex;
        gap: 8px;
        align-items: center;
        color: var(--primary-text-color);
      }
      .check input {
        width: auto;
        min-height: 0;
      }
      button ha-icon {
        --mdc-icon-size: 18px;
      }
      .preview {
        margin-top: 16px;
      }
    `];
	}
};
R([N({ attribute: !1 })], q.prototype, "ctx", void 0), R([P()], q.prototype, "data", void 0), R([P()], q.prototype, "preview", void 0), R([P()], q.prototype, "includeSettings", void 0), R([P()], q.prototype, "error", void 0), R([P()], q.prototype, "busy", void 0), q = R([M("bg-backup")], q);
// src/logic/table.ts
var gt = {
	search: "",
	source: "all",
	kind: "all",
	sort: "created_at",
	dir: "desc"
};
function _t(e, t) {
	if (!t) return !0;
	let n = [
		e.ip,
		e.reason,
		e.country ?? "",
		e.city ?? "",
		e.created_by ?? ""
	].join(" ").toLowerCase();
	return t.toLowerCase().split(/\s+/).filter(Boolean).every((e) => n.includes(e));
}
function vt(e, t) {
	switch (t) {
		case "permanent": return e.expires_at === null;
		case "temporary": return e.expires_at !== null;
		case "unenforced": return Ve(e);
		case "network": return !e.single;
		default: return !0;
	}
}
function J(e) {
	let t = e.split("/")[0] ?? e;
	if (t.includes(".") && !t.includes(":")) return "4" + t.split(".").map((e) => e.padStart(3, "0")).join("");
	let [n = "", r = ""] = t.split("::"), i = n ? n.split(":") : [], a = r ? r.split(":") : [], o = t.includes("::") ? Array(8 - i.length - a.length).fill("0") : [];
	return "6" + [
		...i,
		...o,
		...a
	].map((e) => e.padStart(4, "0")).join("");
}
function yt(e, t, n) {
	switch (n) {
		case "ip": return J(e.ip).localeCompare(J(t.ip));
		case "expires_at": {
			let n = e.expires_at ? Date.parse(e.expires_at) : Infinity, r = t.expires_at ? Date.parse(t.expires_at) : Infinity;
			return n === r ? 0 : n < r ? -1 : 1;
		}
		case "created_at": return Date.parse(e.created_at) - Date.parse(t.created_at);
		case "country": return e.country === t.country ? 0 : e.country === null ? 1 : t.country === null ? -1 : e.country.localeCompare(t.country);
		case "source": return e.source.localeCompare(t.source);
	}
}
function bt(e, t) {
	let n = e.filter((e) => _t(e, t.search.trim()) && (t.source === "all" || e.source === t.source) && vt(e, t.kind)), r = t.dir === "asc" ? 1 : -1;
	return n.sort((e, n) => r * yt(e, n, t.sort) || J(e.ip).localeCompare(J(n.ip)));
}
function xt(e, t) {
	return e.sort === t ? {
		...e,
		dir: e.dir === "asc" ? "desc" : "asc"
	} : {
		...e,
		sort: t,
		dir: t === "ip" || t === "country" ? "asc" : "desc"
	};
}
// src/views/bans.ts
var St = [
	"all",
	"manual",
	"automatic",
	"service",
	"imported",
	"home_assistant"
], Ct = [
	"all",
	"permanent",
	"temporary",
	"network",
	"unenforced"
], Y = class extends j {
	constructor(...e) {
		super(...e), this.revision = 0, this.bans = null, this.query = { ...gt }, this.selected = /* @__PURE__ */ new Set(), this.now = Date.now(), this.adding = !1, this.form = {
			ips: "",
			reason: "",
			duration: "permanent"
		}, this.formError = "", this.busy = !1;
	}
	connectedCallback() {
		super.connectedCallback(), this.ticker = window.setInterval(() => {
			this.now = Date.now();
		}, 1e3);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), window.clearInterval(this.ticker);
	}
	updated(e) {
		(e.has("revision") || e.has("ctx")) && this.load();
	}
	async load() {
		try {
			this.bans = await this.ctx.api.bans();
			let e = new Set(this.bans.map((e) => e.ip));
			this.selected = new Set([...this.selected].filter((t) => e.has(t)));
		} catch (e) {
			this.ctx.error(e);
		}
	}
	async unban(e) {
		let { t } = this.ctx;
		if (await this.ctx.confirm({
			title: t("bans.confirm_unban_title", { count: e.length }),
			body: t("bans.confirm_unban_body", { list: e.slice(0, 10).join(", ") + (e.length > 10 ? " …" : "") }),
			confirm: t("bans.unban"),
			destructive: !0
		})) try {
			let n = await this.ctx.api.unban(e);
			this.selected = /* @__PURE__ */ new Set(), this.ctx.toast({
				message: t("bans.unbanned", { count: n.length }),
				actionLabel: t("common.undo"),
				action: async () => {
					try {
						await this.ctx.api.restore(n);
					} catch (e) {
						this.ctx.error(e);
					}
				}
			});
		} catch (e) {
			this.ctx.error(e);
		}
	}
	async submit(e) {
		e.preventDefault();
		let { t } = this.ctx, n = ft(this.form.ips), r = n.find((e) => !lt(e));
		if (!n.length || r !== void 0) this.formError = t("bans.invalid_ip", { value: r ?? "" });
		else if (!mt(this.form.duration)) this.formError = t("bans.invalid_duration");
		else {
			this.busy = !0, this.formError = "";
			try {
				let e = [];
				for (let t of n) e.push(await this.ctx.api.ban(t, this.form.reason, this.form.duration));
				this.adding = !1, this.form = {
					ips: "",
					reason: "",
					duration: "permanent"
				};
				let r = e.filter(Ve);
				r.length ? await this.warnUnenforced(r) : this.ctx.toast({ message: t("bans.banned", { ip: n.join(", ") }) });
			} catch (e) {
				this.formError = I(e, t);
			} finally {
				this.busy = !1;
			}
		}
	}
	async warnUnenforced(e) {
		let { t } = this.ctx, n = e.map((e) => `${e.ip}: ${B(e.enforcement, t).detail}`), r = e.filter((e) => e.enforcement && !e.enforcement.enforced);
		if (!r.length) this.ctx.toast({
			message: `${t("bans.partial_title")}. ${n.join(" ")}`,
			duration: 15e3
		});
		else if (await this.ctx.confirm({
			title: t("bans.unenforced_title", { count: r.length }),
			body: `${n.join(" ")} ${t("bans.unenforced_body")}`,
			confirm: t("bans.unenforced_remove"),
			cancel: t("bans.unenforced_keep"),
			destructive: !0
		})) try {
			await this.ctx.api.unban(r.map((e) => e.ip));
		} catch (e) {
			this.ctx.error(e);
		}
	}
	toggle(e, t) {
		let n = new Set(this.selected);
		t ? n.add(e) : n.delete(e), this.selected = n;
	}
	header(e, t, n = "") {
		let r = this.query.sort === e;
		return w`<th aria-sort=${r ? this.query.dir === "asc" ? "ascending" : "descending" : "none"} class=${n}>
      <button
        @click=${() => this.query = xt(this.query, e)}
        aria-label=${this.ctx.t("bans.sort_by", { column: t })}
      >
        ${t}${r ? this.query.dir === "asc" ? " ▲" : " ▼" : ""}
      </button>
    </th>`;
	}
	enforcementChip(e) {
		let t = B(e.enforcement, this.ctx.t);
		return t.level === "ok" ? E : w`<div class="enforcement">
      <span class="chip ${t.level === "off" ? "bad" : "warn"}">${t.label}</span>
      <span class="why">${t.detail}</span>
    </div>`;
	}
	expiry(e) {
		let { t } = this.ctx, n = He(e.expires_at, this.now);
		return n ? n.expired ? w`<span class="chip">${t("common.expired")}</span>` : w`<span class="chip warn" title=${H(e.expires_at, this.ctx.language)}>
      ${Ue(n)}
    </span>` : w`<span class="chip">${t("common.permanent")}</span>`;
	}
	renderDialog() {
		let { t: e } = this.ctx;
		return w`<bg-dialog
      .open=${this.adding}
      .heading=${e("bans.add_title")}
      @closed=${() => this.adding = !1}
    >
      <form id="ban-form" @submit=${this.submit}>
        <label for="ips">${e("bans.ip_label")}</label>
        <textarea
          id="ips"
          rows="2"
          required
          aria-describedby="ips-help"
          .value=${this.form.ips}
          @input=${(e) => this.form = {
			...this.form,
			ips: e.target.value
		}}
        ></textarea>
        <div class="help" id="ips-help">${e("bans.ip_help")}</div>
        <label for="reason">${e("bans.reason_label")}</label>
        <input
          id="reason"
          maxlength="200"
          .value=${this.form.reason}
          @input=${(e) => this.form = {
			...this.form,
			reason: e.target.value
		}}
        />
        <label for="duration">${e("bans.duration_label")}</label>
        <input
          id="duration"
          list="durations"
          aria-describedby="duration-help"
          .value=${this.form.duration}
          @input=${(e) => this.form = {
			...this.form,
			duration: e.target.value
		}}
        />
        <datalist id="durations">
          ${[
			"1h",
			"24h",
			"7d",
			"30d",
			"permanent"
		].map((e) => w`<option value=${e}></option>`)}
        </datalist>
        <div class="help" id="duration-help">${e("bans.duration_help")}</div>
        ${this.formError ? w`<div class="error" role="alert">${this.formError}</div>` : E}
      </form>
      <button slot="actions" @click=${() => this.adding = !1}>
        ${e("common.cancel")}
      </button>
      <button
        slot="actions"
        class="primary"
        type="submit"
        form="ban-form"
        ?disabled=${this.busy}
      >
        ${e("bans.add")}
      </button>
    </bg-dialog>`;
	}
	render() {
		let { t: e, language: t } = this.ctx;
		if (this.bans === null) return w`<p class="muted">${e("common.loading")}</p>`;
		let n = bt(this.bans, this.query), r = n.length > 0 && n.every((e) => this.selected.has(e.ip)), i = w`<div class="row toolbar">
      <input
        type="search"
        class="search"
        placeholder=${e("common.search")}
        aria-label=${e("common.search")}
        .value=${this.query.search}
        @input=${(e) => this.query = {
			...this.query,
			search: e.target.value
		}}
      />
      <select
        aria-label=${e("bans.filter_source")}
        @change=${(e) => this.query = {
			...this.query,
			source: e.target.value
		}}
      >
        ${St.map((t) => w`<option value=${t} ?selected=${this.query.source === t}>
              ${e(`bans.source_${t}`)}
            </option>`)}
      </select>
      <select
        aria-label=${e("bans.filter_kind")}
        @change=${(e) => this.query = {
			...this.query,
			kind: e.target.value
		}}
      >
        ${Ct.map((t) => w`<option value=${t} ?selected=${this.query.kind === t}>
              ${e(`bans.kind_${t}`)}
            </option>`)}
      </select>
      <span class="spacer"></span>
      ${this.selected.size ? w`<button class="danger" @click=${() => this.unban([...this.selected])}>
            ${e("bans.unban_selected", { count: this.selected.size })}
          </button>` : E}
      <button class="primary" @click=${() => this.adding = !0}>
        ${e("bans.add")}
      </button>
    </div>`;
		return this.bans.length ? w`<ha-card>
        ${i}
        <div class="muted count">
          ${e("bans.count", {
			shown: n.length,
			total: this.bans.length
		})}
        </div>
        ${n.length ? w`<div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>
                      <input
                        type="checkbox"
                        .checked=${r}
                        aria-label=${e("bans.select_all")}
                        @change=${(e) => {
			let t = e.target.checked;
			this.selected = t ? new Set(n.map((e) => e.ip)) : /* @__PURE__ */ new Set();
		}}
                      />
                    </th>
                    ${this.header("ip", e("bans.col_ip"))}
                    ${this.header("country", e("bans.col_country"), "hide-narrow")}
                    <th class="hide-narrow">${e("bans.col_reason")}</th>
                    ${this.header("source", e("bans.col_source"), "hide-narrow")}
                    ${this.header("created_at", e("bans.col_created"), "hide-narrow")}
                    ${this.header("expires_at", e("bans.col_expires"))}
                    <th><span class="sr-only">${e("bans.unban")}</span></th>
                  </tr>
                </thead>
                <tbody>
                  ${n.map((n) => w`<tr>
                      <td>
                        <input
                          type="checkbox"
                          .checked=${this.selected.has(n.ip)}
                          aria-label=${e("bans.select_one", { ip: n.ip })}
                          @change=${(e) => this.toggle(n.ip, e.target.checked)}
                        />
                      </td>
                      <td>
                        <button
                          class="link mono"
                          @click=${() => this.ctx.openDetails(n.ip)}
                          aria-label=${e("common.details", { ip: n.ip })}
                        >
                          ${n.ip}
                        </button>
                        ${this.enforcementChip(n)}
                      </td>
                      <td class="hide-narrow" title=${n.city ?? ""}>
                        ${n.country ? `${V(n.country)} ${n.country}` : ""}
                      </td>
                      <td class="hide-narrow reason">${n.reason}</td>
                      <td class="hide-narrow">
                        <span class="chip">${e(`bans.source_${n.source}`)}</span>
                      </td>
                      <td class="hide-narrow">${H(n.created_at, t)}</td>
                      <td>${this.expiry(n)}</td>
                      <td>
                        <button
                          class="icon"
                          @click=${() => this.unban([n.ip])}
                          aria-label=${`${e("bans.unban")} ${n.ip}`}
                          title=${e("bans.unban")}
                        >
                          <ha-icon icon="mdi:lock-open-variant-outline"></ha-icon>
                        </button>
                      </td>
                    </tr>`)}
                </tbody>
              </table>
            </div>` : w`<p class="muted empty">${e("bans.no_match")}</p>`}
      </ha-card>
      ${this.renderDialog()}` : w`<ha-card class="empty">
          <ha-icon icon="mdi:shield-check-outline" aria-hidden="true"></ha-icon>
          <h3>${e("bans.empty_title")}</h3>
          <p>${e("bans.empty_body")}</p>
          <button class="primary" @click=${() => this.adding = !0}>${e("bans.add")}</button>
        </ha-card>
        ${this.renderDialog()}`;
	}
	static {
		this.styles = [L, o`
      .toolbar {
        margin-bottom: 8px;
      }
      .search {
        flex: 1 1 200px;
        width: auto;
      }
      select {
        width: auto;
      }
      .count {
        font-size: 0.8rem;
        margin-bottom: 4px;
      }
      .link {
        border: none;
        padding: 0;
        min-height: 0;
        border-radius: 0;
        text-align: start;
      }
      .enforcement {
        margin-top: 4px;
        font-size: 0.8rem;
        color: var(--secondary-text-color);
        max-width: 360px;
      }
      .enforcement .why {
        display: block;
        margin-top: 2px;
      }
      .reason {
        max-width: 240px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      textarea {
        resize: vertical;
      }
    `];
	}
};
R([N({ attribute: !1 })], Y.prototype, "ctx", void 0), R([N({ type: Number })], Y.prototype, "revision", void 0), R([P()], Y.prototype, "bans", void 0), R([P()], Y.prototype, "query", void 0), R([P()], Y.prototype, "selected", void 0), R([P()], Y.prototype, "now", void 0), R([P()], Y.prototype, "adding", void 0), R([P()], Y.prototype, "form", void 0), R([P()], Y.prototype, "formError", void 0), R([P()], Y.prototype, "busy", void 0), Y = R([M("bg-bans")], Y);
// src/views/overview.ts
var X = class extends j {
	constructor(...e) {
		super(...e), this.revision = 0, this.data = null, this.failed = !1;
	}
	updated(e) {
		(e.has("revision") || e.has("ctx")) && this.load();
	}
	async load() {
		try {
			this.data = await this.ctx.api.overview(), this.failed = !1;
		} catch (e) {
			this.failed = !0, this.ctx.error(e);
		}
	}
	card(e, t, n, r) {
		let i = w`<ha-icon .icon=${n} aria-hidden="true"></ha-icon>
      <div>
        <div class="value">${t}</div>
        <div class="muted">${e}</div>
      </div>`;
		return r ? w`<button class="card stat" @click=${() => this.ctx.navigate(r)}>${i}</button>` : w`<div class="card stat">${i}</div>`;
	}
	chart(e) {
		let { t, language: n } = this.ctx, r = e.failed_logins_7d, { ratios: i } = We(r.map((e) => e.count)), a = 340 / r.length, o = new Intl.DateTimeFormat(n, { weekday: "short" });
		return w`<figure>
      <svg viewBox="0 0 ${340} ${164}" role="img" aria-label=${t("overview.chart_title")}>
        <line x1="0" y1=${140} x2=${340} y2=${140} class="axis"></line>
        ${r.map((e, n) => {
			let r = Math.max((i[n] ?? 0) * 140, e.count ? 2 : 0), s = n * a + a * .2;
			return Se`<g>
            <title>${t("overview.chart_label", {
				date: e.date,
				count: e.count
			})}</title>
            <rect x=${s} y=${140 - r} width=${a * .6} height=${r} rx="3" class="bar"></rect>
            <text x=${s + a * .3} y=${156} class="tick">${o.format(/* @__PURE__ */ new Date(`${e.date}T12:00:00`))}</text>
            ${e.count ? Se`<text x=${s + a * .3} y=${140 - r - 4} class="count">${e.count}</text>` : E}
          </g>`;
		})}
      </svg>
      <figcaption class="sr-only">
        ${r.map((e) => t("overview.chart_label", {
			date: e.date,
			count: e.count
		})).join(", ")}
      </figcaption>
    </figure>`;
	}
	render() {
		let { t: e, language: t } = this.ctx, n = this.data;
		if (!n) return this.failed ? w`<div class="card empty">
            <button @click=${this.load}>${e("common.retry")}</button>
          </div>` : w`<p class="muted">${e("common.loading")}</p>`;
		let r = n.status.geoip.loaded;
		return w`
      <div class="stats">
        ${this.card(e("overview.active_bans"), n.active_bans, "mdi:shield-lock", "bans")}
        ${this.card(e("overview.bans_24h"), n.bans_24h, "mdi:shield-alert", "activity")}
        ${this.card(e("overview.logins_24h"), n.logins_24h, "mdi:login", "activity")}
        ${this.card(e("overview.failed_24h"), n.failed_logins_24h, "mdi:account-alert", "activity")}
        ${this.card(e("overview.blocked_24h"), n.blocked_24h, "mdi:cancel", "activity")}
        ${this.card(e("overview.allowlist"), n.allowlist, "mdi:playlist-check", "allowlist")}
      </div>
      <div class="grid">
        <ha-card class="chart">
          <h2>${e("overview.chart_title")}</h2>
          ${this.chart(n)}
        </ha-card>
        <ha-card>
          <h2>${e("overview.top_ips")}</h2>
          ${n.top_ips.length ? w`<ol class="list">
                ${n.top_ips.map((t) => w`<li>
                    <button
                      class="link mono"
                      @click=${() => this.ctx.openDetails(t.ip)}
                      aria-label=${e("common.details", { ip: t.ip })}
                    >
                      ${t.ip}
                    </button>
                    <span class="muted">${e("overview.attempts", { count: t.count })}</span>
                  </li>`)}
              </ol>` : w`<p class="muted">${e("overview.no_offenders")}</p>`}
        </ha-card>
        <ha-card>
          <h2>${e("overview.top_countries")}</h2>
          ${r ? n.top_countries.length ? w`<ol class="list">
                  ${n.top_countries.map((t) => w`<li>
                      <span>${V(t.country)} ${t.country}</span>
                      <span class="muted">${e("overview.attempts", { count: t.count })}</span>
                    </li>`)}
                </ol>` : w`<p class="muted">${e("overview.no_offenders")}</p>` : w`<p class="muted">${e("overview.countries_need_geoip")}</p>`}
          ${n.last_ban ? w`<h2 class="last">${e("overview.last_ban")}</h2>
                <button class="link mono" @click=${() => this.ctx.openDetails(n.last_ban?.ip ?? "")}>
                  ${V(n.last_ban.country)} ${n.last_ban.ip}
                </button>
                <div class="muted">
                  ${H(n.last_ban.created_at, t)} · ${n.last_ban.reason}
                </div>` : E}
        </ha-card>
      </div>
    `;
	}
	static {
		this.styles = [L, o`
      .stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin-bottom: 12px;
      }
      .stat {
        display: flex;
        gap: 12px;
        align-items: center;
        text-align: start;
        width: 100%;
        color: inherit;
        font-weight: normal;
        border-radius: var(--ha-card-border-radius, 12px);
      }
      .stat ha-icon {
        color: var(--primary-color);
        --mdc-icon-size: 32px;
      }
      .value {
        font-size: 1.8rem;
        font-weight: 500;
        line-height: 1.1;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 12px;
      }
      figure {
        margin: 0;
      }
      svg {
        width: 100%;
        height: auto;
      }
      .bar {
        fill: var(--primary-color);
      }
      .axis {
        stroke: var(--divider-color);
      }
      .tick,
      .count {
        font-size: 10px;
        text-anchor: middle;
        fill: var(--secondary-text-color);
      }
      .list {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .list li {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 6px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .link {
        border: none;
        padding: 0;
        min-height: 0;
        border-radius: 0;
        text-align: start;
      }
      .last {
        margin-top: 16px;
      }
    `];
	}
};
R([N({ attribute: !1 })], X.prototype, "ctx", void 0), R([N({ type: Number })], X.prototype, "revision", void 0), R([P()], X.prototype, "data", void 0), R([P()], X.prototype, "failed", void 0), X = R([M("bg-overview")], X);
// src/views/settings.ts
var Z = class extends j {
	constructor(...e) {
		super(...e), this.settings = null, this.syncing = !1;
	}
	openOptions() {
		history.pushState(null, "", "/config/integrations/integration/ban_guard"), window.dispatchEvent(new CustomEvent("location-changed"));
	}
	async sync() {
		let { t: e } = this.ctx;
		this.syncing = !0;
		try {
			let t = await this.ctx.api.npmSync();
			this.ctx.toast({ message: t.ok ? e("settings.npm_synced", { count: t.count ?? 0 }) : e("settings.npm_failed", { error: t.error ?? "?" }) });
		} catch (t) {
			this.ctx.toast({ message: I(t, e) });
		} finally {
			this.syncing = !1;
		}
	}
	item(e, t) {
		return w`<div class="item">
      <dt>${e}</dt>
      <dd>${t}</dd>
    </div>`;
	}
	render() {
		let { t: e } = this.ctx, t = this.settings;
		if (!t) return w`<p class="muted">${e("common.loading")}</p>`;
		let n = t.options, r = (t) => e(t ? "settings.on" : "settings.off"), i = t.status.geoip, a = [];
		return i.enabled && a.push("download.db-ip.com (GeoIP)"), t.status.rdns && !t.status.doh && a.push(e("settings.rdns")), t.status.doh && a.push(String(n.doh_url ?? "")), t.status.npm.enabled && a.push(String(n.npm_url ?? "")), w`<ha-card>
      <p class="muted">${e("settings.intro")}</p>
      ${t.requester_ip ? w`<p><ha-icon icon="mdi:account-lock"></ha-icon>
            ${e("settings.your_ip", { ip: t.requester_ip })}</p>` : E}
      <dl>
        ${this.item(e("settings.protection"), n.protection_enabled ? e("settings.protection_value", {
			threshold: String(n.threshold),
			window: String(n.window_minutes),
			ladder: String(n.escalation)
		}) : e("settings.off"))}
        ${this.item(e("settings.logins"), r(t.status.login_logging))}
        ${this.item(e("settings.sessions"), r(t.status.session_closing))}
        ${this.item(e("settings.notifications"), r(n.notify_persistent))}
        ${this.item(e("settings.logging"), e("settings.logging_value", {
			days: String(n.log_retention_days),
			entries: String(n.log_max_entries)
		}))}
        ${this.item(e("settings.geoip"), i.enabled ? i.error ? e("settings.geoip_error", { error: i.error }) : i.loaded ? e("settings.geoip_loaded", { edition: i.edition }) : e("settings.geoip_loading") : e("settings.off"))}
        ${this.item(e("settings.rdns"), r(t.status.rdns))}
        ${this.item(e("settings.doh"), r(t.status.doh))}
        ${this.item(e("settings.countries"), e("settings.countries_value", {
			allow: t.status.country_rules.allow.join(", ") || e("common.none"),
			deny: t.status.country_rules.deny.join(", ") || e("common.none")
		}))}
        ${this.item(e("settings.npm"), r(t.status.npm.enabled))}
      </dl>
      ${t.npm_addon ? w`<p class="muted">${e("settings.npm_detected", { name: t.npm_addon.name })}</p>` : E}
      <h2>${e("settings.privacy")}</h2>
      ${a.length ? w`<ul>
            ${a.map((e) => w`<li class="mono">${e}</li>`)}
          </ul>` : w`<p class="muted">${e("settings.privacy_none")}</p>`}
      <div class="row">
        <button class="primary" @click=${this.openOptions}>
          <ha-icon icon="mdi:cog"></ha-icon> ${e("settings.open_options")}
        </button>
        ${t.status.npm.enabled ? w`<button ?disabled=${this.syncing} @click=${this.sync}>
              ${e("settings.npm_sync")}
            </button>` : E}
      </div>
    </ha-card>`;
	}
	static {
		this.styles = [L, o`
      dl {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 12px;
        margin: 16px 0;
      }
      .item {
        padding: 12px;
        border-radius: 8px;
        background: var(--secondary-background-color);
      }
      dt {
        font-size: 0.8rem;
        color: var(--secondary-text-color);
      }
      dd {
        margin: 4px 0 0;
      }
      button ha-icon {
        --mdc-icon-size: 18px;
      }
    `];
	}
};
R([N({ attribute: !1 })], Z.prototype, "ctx", void 0), R([N({ attribute: !1 })], Z.prototype, "settings", void 0), R([P()], Z.prototype, "syncing", void 0), Z = R([M("bg-settings")], Z);
// src/ban-guard-panel.ts
var Q = [
	{
		id: "overview",
		icon: "mdi:view-dashboard-outline"
	},
	{
		id: "bans",
		icon: "mdi:shield-lock-outline"
	},
	{
		id: "allowlist",
		icon: "mdi:playlist-check"
	},
	{
		id: "activity",
		icon: "mdi:timeline-clock-outline"
	},
	{
		id: "settings",
		icon: "mdi:cog-outline"
	},
	{
		id: "backup",
		icon: "mdi:swap-vertical"
	}
], $ = class extends j {
	constructor(...e) {
		super(...e), this.narrow = !1, this.tab = "overview", this.revision = 0, this.details = null, this.settings = null, this.api = null, this.ctx = null, this.language = "", this.unsub = null;
	}
	connectedCallback() {
		super.connectedCallback();
		let e = location.hash.slice(1);
		Q.some((t) => t.id === e) && (this.tab = e), this.hass && this.subscribe();
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this.unsub?.(), this.unsub = null, window.clearTimeout(this.refreshTimer);
	}
	willUpdate(e) {
		if (!e.has("hass") || !this.hass) return;
		let t = this.hass.locale?.language ?? this.hass.language ?? "en", n = this.api === null;
		(n || t !== this.language) && (this.language = t, this.api ??= new ze(this.hass), this.ctx = this.makeCtx(this.api, Qe(t))), n && (this.subscribe(), this.loadSettings());
	}
	makeCtx(e, t) {
		return {
			hass: this.hass,
			api: e,
			t,
			language: this.language,
			confirm: (e) => this.confirmEl.ask({
				...e,
				confirm: e.confirm ?? t("common.confirm"),
				cancel: e.cancel ?? t("common.cancel")
			}),
			toast: (e) => this.toastEl.show(e),
			error: (e) => this.toastEl.show({ message: I(e, t) }),
			openDetails: (e) => this.details = e,
			navigate: (e) => this.select(e)
		};
	}
	async subscribe() {
		if (!this.unsub && this.api) try {
			this.unsub = await this.api.subscribeUpdates(() => this.scheduleRefresh());
		} catch {}
	}
	scheduleRefresh() {
		this.refreshTimer === void 0 && (this.refreshTimer = window.setTimeout(() => {
			this.refreshTimer = void 0, this.revision += 1;
		}, 750));
	}
	async loadSettings() {
		try {
			this.api && (this.settings = await this.api.settings());
		} catch (e) {
			this.ctx?.error(e);
		}
	}
	select(e) {
		this.tab = e, history.replaceState(null, "", `#${e}`), e === "settings" && this.loadSettings();
	}
	onTabKey(e) {
		let t = Q.findIndex((e) => e.id === this.tab), n;
		if (e.key === "ArrowRight") n = (t + 1) % Q.length;
		else if (e.key === "ArrowLeft") n = (t - 1 + Q.length) % Q.length;
		else if (e.key === "Home") n = 0;
		else if (e.key === "End") n = Q.length - 1;
		else return;
		e.preventDefault();
		let r = Q[n]?.id ?? "overview";
		this.select(r), this.updateComplete.then(() => this.renderRoot.querySelector(`#tab-${r}`)?.focus());
	}
	banners() {
		let e = this.settings?.status;
		if (!e || !this.ctx) return E;
		let t = this.ctx.t, n = [];
		if (e.hook !== "active") {
			let r = [
				"incompatible",
				"ip_ban_disabled",
				"error"
			].includes(e.hook) ? `status.hook_${e.hook}` : "status.hook_other";
			n.push(w`<div class="banner bad" role="alert">${t(r, { status: e.hook })}</div>`);
		}
		return e.under_attack && n.push(w`<div class="banner bad" role="alert">${t("status.under_attack")}</div>`), e.protection_enabled || n.push(w`<div class="banner">${t("status.protection_off")}</div>`), n;
	}
	view() {
		let e = this.ctx;
		if (!e) return E;
		switch (this.tab) {
			case "overview": return w`<bg-overview .ctx=${e} .revision=${this.revision}></bg-overview>`;
			case "bans": return w`<bg-bans .ctx=${e} .revision=${this.revision}></bg-bans>`;
			case "allowlist": return w`<bg-allowlist
          .ctx=${e}
          .revision=${this.revision}
          .requesterIp=${this.settings?.requester_ip ?? null}
        ></bg-allowlist>`;
			case "activity": return w`<bg-activity .ctx=${e}></bg-activity>`;
			case "settings": return w`<bg-settings .ctx=${e} .settings=${this.settings}></bg-settings>`;
			case "backup": return w`<bg-backup .ctx=${e}></bg-backup>`;
		}
	}
	render() {
		if (!this.ctx) return E;
		let e = this.ctx.t;
		return w`
      <header class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <h1>${e("title")}</h1>
      </header>
      <nav role="tablist" aria-label=${e("title")} @keydown=${this.onTabKey}>
        ${Q.map((t) => w`<button
            role="tab"
            id="tab-${t.id}"
            aria-selected=${this.tab === t.id}
            aria-controls="panel"
            tabindex=${this.tab === t.id ? 0 : -1}
            @click=${() => this.select(t.id)}
          >
            <ha-icon .icon=${t.icon} aria-hidden="true"></ha-icon>
            <span>${e(`tabs.${t.id}`)}</span>
          </button>`)}
      </nav>
      <main id="panel" role="tabpanel" aria-labelledby="tab-${this.tab}">
        ${this.banners()} ${this.view()}
      </main>
      <bg-drawer
        .ctx=${this.ctx}
        .ip=${this.details}
        .revision=${this.revision}
        @closed=${() => this.details = null}
      ></bg-drawer>
      <bg-confirm></bg-confirm>
      <bg-toast></bg-toast>
    `;
	}
	static {
		this.styles = [L, o`
      :host {
        display: block;
        min-height: 100vh;
        background: var(--primary-background-color);
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        height: var(--header-height, 56px);
        padding: 0 12px;
        background: var(--app-header-background-color, var(--primary-background-color));
        color: var(--app-header-text-color, var(--primary-text-color));
        border-bottom: var(--app-header-border-bottom, 1px solid var(--divider-color));
      }
      h1 {
        font-size: 1.25rem;
        font-weight: 400;
        margin: 0;
      }
      nav {
        display: flex;
        gap: 4px;
        overflow-x: auto;
        padding: 8px 12px 0;
        border-bottom: 1px solid var(--divider-color);
        scrollbar-width: none;
      }
      nav button {
        display: flex;
        align-items: center;
        gap: 6px;
        border: none;
        border-radius: 0;
        border-bottom: 2px solid transparent;
        color: var(--secondary-text-color);
        padding: 8px 12px;
        white-space: nowrap;
      }
      nav button[aria-selected="true"] {
        color: var(--primary-color);
        border-bottom-color: var(--primary-color);
      }
      nav ha-icon {
        --mdc-icon-size: 20px;
      }
      main {
        padding: 16px;
        max-width: 1200px;
        margin: 0 auto;
      }
      @media (max-width: 600px) {
        main {
          padding: 8px;
        }
        nav span {
          display: none;
        }
        nav button[aria-selected="true"] span {
          display: inline;
        }
      }
    `];
	}
};
R([N({ attribute: !1 })], $.prototype, "hass", void 0), R([N({ type: Boolean })], $.prototype, "narrow", void 0), R([P()], $.prototype, "tab", void 0), R([P()], $.prototype, "revision", void 0), R([P()], $.prototype, "details", void 0), R([P()], $.prototype, "settings", void 0), R([F("bg-confirm")], $.prototype, "confirmEl", void 0), R([F("bg-toast")], $.prototype, "toastEl", void 0), $ = R([M("ban-guard-panel")], $);
export { $ as BanGuardPanel };
