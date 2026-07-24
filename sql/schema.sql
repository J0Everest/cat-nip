IF DB_ID('Catapult') IS NULL
BEGIN
  CREATE DATABASE Catapult;
END
GO

USE Catapult;
GO

IF OBJECT_ID('dbo.pricing_history', 'U') IS NOT NULL
  DROP TABLE dbo.pricing_history;
GO

CREATE TABLE dbo.pricing_history (
  id INT IDENTITY(1,1) PRIMARY KEY,
  group_no INT NOT NULL,
  as_of_date DATE NOT NULL,
  [status] VARCHAR(20) NOT NULL,
  layer_desc VARCHAR(80) NOT NULL,
  terms VARCHAR(80) NOT NULL,
  curr VARCHAR(10) NOT NULL,
  reinst VARCHAR(30) NOT NULL,
  rol VARCHAR(20) NOT NULL,
  cr VARCHAR(20) NOT NULL,
  sdf VARCHAR(20) NOT NULL,
  roe VARCHAR(20) NOT NULL,
  final_share VARCHAR(20) NOT NULL,
  our_limit VARCHAR(30) NOT NULL,
  our_premium VARCHAR(30) NOT NULL,
  final_rate VARCHAR(20) NOT NULL,
  subject_base VARCHAR(30) NOT NULL,
  contract VARCHAR(60) NOT NULL,
  user_name VARCHAR(120) NOT NULL
);
GO

INSERT INTO dbo.pricing_history
(group_no, as_of_date, [status], layer_desc, terms, curr, reinst, rol, cr, sdf, roe, final_share, our_limit, our_premium, final_rate, subject_base, contract, user_name)
VALUES
(1,'2026-06-01','Quoted','Layer 1','CAT: 42.5x17.5','USD','1@100;','10.00%','66.28%','16.47%','7.10%','15.00%','6,375,000','637,500','0.65%','1,000,000,000','TP10003708-2026-1','Judah Orlinsky'),
(1,'2026-06-05','Authorized','Layer 1','CAT: 42.5x17.5','USD','1@100;','12.00%','56.85%','25.28%','11.13%','15.00%','6,375,000','765,000','0.51%','1,000,000,000','TP10003708-2026-1','Judah Orlinsky'),
(1,'2026-06-10','Bound','Layer 1','CAT: 42.5x17.5','USD','1@100;','15.25%','46.81%','39.61%','18.08%','15.00%','6,375,000','972,188','0.65%','1,000,000,000','TP10003708-2026-1','Judah Orlinsky'),
(2,'2026-06-01','Quoted','Layer 2','CAT: 105x60','USD','1@100;','3.90%','58.10%','19.40%','8.25%','15.00%','15,750,000','614,250','0.41%','1,000,000,000','TP10003708-2026-2','Judah Orlinsky'),
(2,'2026-06-05','Authorized','Layer 2','CAT: 105x60','USD','1@100;','4.20%','54.20%','22.10%','9.60%','15.00%','15,750,000','661,500','0.44%','1,000,000,000','TP10003708-2026-2','Judah Orlinsky'),
(2,'2026-06-10','Bound','Layer 2','CAT: 105x60','USD','1@100;','4.75%','45.79%','22.41%','11.08%','15.00%','15,750,000','748,125','0.50%','1,000,000,000','TP10003708-2026-2','Judah Orlinsky');
GO
