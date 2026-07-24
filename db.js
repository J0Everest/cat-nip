const useWindowsAuth =
  String(process.env.DB_INTEGRATED_SECURITY || "false").toLowerCase() === "true" ||
  String(process.env.DB_AUTH_MODE || "sql").toLowerCase() === "windows";

const sql = useWindowsAuth ? require("mssql/msnodesqlv8") : require("mssql");

function toBool(value, fallback = false) {
  if (value == null) return fallback;
  return String(value).toLowerCase() === "true";
}

function getServerName() {
  // Quarterly change helper: set DB_SERVER_CURRENT without touching older values.
  return process.env.DB_SERVER_CURRENT || process.env.DB_SERVER || "localhost";
}

function buildWindowsConnectionString(database) {
  const server = getServerName();
  const encrypt = toBool(process.env.DB_ENCRYPT, false) ? "Yes" : "No";
  const trustServerCertificate = toBool(process.env.DB_TRUST_SERVER_CERT, false) ? "Yes" : "No";
  const timeoutSeconds = Number(process.env.DB_CONNECT_TIMEOUT || 30);

  return [
    "Driver={ODBC Driver 18 for SQL Server}",
    `Server=${server}`,
    `Database=${database}`,
    "Trusted_Connection=Yes",
    "Persist Security Info=False",
    "Pooling=False",
    "MultipleActiveResultSets=False",
    `Encrypt=${encrypt}`,
    `TrustServerCertificate=${trustServerCertificate}`,
    "Packet Size=4096",
    `Connection Timeout=${timeoutSeconds}`
  ].join(";");
}

function buildConfig(database) {
  if (useWindowsAuth) {
    return {
      connectionString: buildWindowsConnectionString(database),
      pool: {
        max: 10,
        min: 0,
        idleTimeoutMillis: 30000
      }
    };
  }

  return {
    server: getServerName(),
    database,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    port: Number(process.env.DB_PORT || 1433),
    options: {
      encrypt: toBool(process.env.DB_ENCRYPT, false),
      trustServerCertificate: toBool(process.env.DB_TRUST_SERVER_CERT, true)
    },
    pool: {
      max: 10,
      min: 0,
      idleTimeoutMillis: 30000
    }
  };
}

let poolPromise;
let catAccumPoolPromise;

function getPool() {
  if (!poolPromise) {
    const database = process.env.DB_DATABASE;
    poolPromise = new sql.ConnectionPool(buildConfig(database))
      .connect()
      .then((pool) => {
        console.log(`Connected to SQL Server (${database})`);
        return pool;
      });
  }

  return poolPromise;
}

function getCatAccumPool() {
  if (!catAccumPoolPromise) {
    const database = process.env.DB_CATACCUM_DATABASE || "CatAccum";
    catAccumPoolPromise = new sql.ConnectionPool(buildConfig(database))
      .connect()
      .then((pool) => {
        console.log(`Connected to SQL Server (${database})`);
        return pool;
      });
  }

  return catAccumPoolPromise;
}

module.exports = { sql, getPool, getCatAccumPool };
