"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { classifyTail } = require(path.join(__dirname, "tail-quadrant.cjs"));

const request = JSON.parse(fs.readFileSync(0, "utf8"));
const brokerage = request.brokerage && Object.keys(request.brokerage).length
  ? new Map(Object.entries(request.brokerage)) : undefined;
const result = classifyTail(request.items, {
  attnQ: request.attention_quantile,
  growthQ: request.growth_quantile,
  minCohort: request.min_cohort,
  maxTailFraction: request.max_tail_fraction,
  growthProxy: request.growth_proxy,
  brokerage,
});
process.stdout.write(JSON.stringify(result));
