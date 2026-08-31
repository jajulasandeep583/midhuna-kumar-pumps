// Entry point for the desk bundle.
//
// These two files used to be listed in app_include_js by raw /assets path.
// Raw asset paths carry no content hash, so browsers cached them for the full
// 12-hour max-age and kept running old code after a deploy - the management
// screens rendered unstyled because the browser was holding a kumar.css from
// before the .kd-* rules existed. Going through the bundler gets each build a
// fresh hashed filename, so a deploy invalidates the cache by construction.
import "./kumar_common.js";
import "./kumar_dashboard.js";
// Registers form handlers for Service Request and Kumar Warranty Claim. It lives
// in the shared bundle rather than doctype_js because it covers two doctypes that
// already have a script of their own, and its handlers simply never fire
// anywhere else.
import "./dealer_reply.js";
// The chat panel that used to sit on the Service Request and Warranty Claim
// forms is gone. It existed because frappe's comment timeline reads as an audit
// log rather than a conversation - but the desk answers that properly now, and
// two chat UIs over one thread is worse than either alone.
