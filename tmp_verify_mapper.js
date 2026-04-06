
// Mock regionalData
const regionalData = {
  "מחוז צפון": {
    "צפת": { "lat": 32.96, "long": 35.49 },
    "טבריה": { "lat": 32.79, "long": 35.53 }
  },
  "מחוז מרכז": {
    "תל אביב - יפו": { "lat": 32.08, "long": 34.78 },
    "ראשון לציון": { "lat": 31.97, "long": 34.80 }
  }
};

// Mock cities array
const cities = [
  { name: "צפת" },
  { name: "תל אביב - יפו" },
  { name: "ראשון לציון" },
  { name: "Unknown City" }
];

const groupCitiesByArea = (cities, regionalData) => {
  if (!cities || !regionalData) return {};
  const groups = {};
  cities.forEach(c => {
    let foundArea = "Other";
    for (const [area, areaCities] of Object.entries(regionalData)) {
      if (areaCities[c.name]) { foundArea = area; break; }
    }
    if (!groups[foundArea]) groups[foundArea] = [];
    groups[foundArea].push(c.name);
  });
  return groups;
};

const result = groupCitiesByArea(cities, regionalData);
console.log("Grouped Result:", JSON.stringify(result, null, 2));

// Expected Output:
// {
//   "מחוז צפון": ["צפת"],
//   "מחוז מרכז": ["תל אביב - יפו", "ראשון לציון"],
//   "Other": ["Unknown City"]
// }

const expected = {
  "מחוז צפון": ["צפת"],
  "מחוז מרכז": ["תל אביב - יפו", "ראשון לציון"],
  "Other": ["Unknown City"]
};

if (JSON.stringify(result) === JSON.stringify(expected)) {
  console.log("Verification [Mapper Logic]: SUCCESS");
} else {
  console.log("Verification [Mapper Logic]: FAILED");
  process.exit(1);
}
