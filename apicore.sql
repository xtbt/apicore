-- phpMyAdmin SQL Dump
-- version 5.1.0
-- https://www.phpmyadmin.net/
--
-- Host: localhost:8889
-- Generation Time: Nov 09, 2026 at 05:13 AM
-- Server version: 5.7.32
-- PHP Version: 8.0.3

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `apicore`
--
DROP DATABASE IF EXISTS `apicore`;
CREATE DATABASE IF NOT EXISTS `apicore` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `apicore`;

-- --------------------------------------------------------

--
-- Table structure for table `moods`
--

DROP TABLE IF EXISTS `moods`;
CREATE TABLE `moods` (
  `MoodId` int(10) UNSIGNED NOT NULL,
  `MoodName` varchar(16) NOT NULL,
  `MoodStatus` enum('Active','Inactive') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Dumping data for table `moods`
--

INSERT INTO `moods` (`MoodId`, `MoodName`, `MoodStatus`) VALUES
(6, 'Hungry', 'Inactive'),
(7, 'Bored', 'Active'),
(9, 'Scared', 'Inactive'),
(10, 'Tired', 'Active'),
(14, 'Very Sad', 'Active'),
(15, 'Very Relaxed', 'Active'),
(16, 'Fearless', 'Active'),
(17, 'Very Fearless', 'Active'),
(18, 'Motivated', 'Inactive');

-- --------------------------------------------------------

--
-- Table structure for table `example`
--
-- Reference entity: one column per common MySQL data type, so a student can
-- copy the pattern (SQL + model + schema + controller + router) for their own
-- tables. Every column is optional except the name, so a minimal POST is
-- {"ExampleName": "..."}.
--

DROP TABLE IF EXISTS `example`;
CREATE TABLE `example` (
  `ExampleId` int(10) UNSIGNED NOT NULL,
  `ExampleName` varchar(45) NOT NULL COMMENT 'varchar: short text with a length limit',
  `ExampleCode` char(3) DEFAULT NULL COMMENT 'char: fixed-length text',
  `ExampleDescription` text COMMENT 'text: long free text',
  `ExamplePrice` decimal(10,2) NOT NULL DEFAULT '0.00' COMMENT 'decimal: exact money amount',
  `ExampleQuantity` int(11) NOT NULL DEFAULT '0' COMMENT 'int: whole number',
  `ExampleBigNumber` bigint(20) NOT NULL DEFAULT '0' COMMENT 'bigint: very large whole number',
  `ExampleRatio` float NOT NULL DEFAULT '0' COMMENT 'float: approximate number',
  `ExampleActive` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'tinyint(1): boolean (0 = false, 1 = true)',
  `ExampleStatus` enum('Active','Inactive') NOT NULL DEFAULT 'Active' COMMENT 'enum: one value from a fixed list',
  `ExampleBirthDate` date DEFAULT NULL COMMENT 'date: calendar day (YYYY-MM-DD)',
  `ExampleCreatedAt` datetime DEFAULT NULL COMMENT 'datetime: date and time (YYYY-MM-DD HH:MM:SS)',
  `ExampleStartTime` time DEFAULT NULL COMMENT 'time: time of day (HH:MM:SS)',
  `ExampleYear` year(4) DEFAULT NULL COMMENT 'year: four-digit year',
  `ExampleMetadata` json DEFAULT NULL COMMENT 'json: structured object or array',
  `ExamplePicture` blob COMMENT 'blob: binary data, sent and received as base64'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Reference table: one column per common data type';

--
-- Dumping data for table `example`
--

INSERT INTO `example` (`ExampleId`, `ExampleName`, `ExampleCode`, `ExampleDescription`, `ExamplePrice`, `ExampleQuantity`, `ExampleBigNumber`, `ExampleRatio`, `ExampleActive`, `ExampleStatus`, `ExampleBirthDate`, `ExampleCreatedAt`, `ExampleStartTime`, `ExampleYear`, `ExampleMetadata`, `ExamplePicture`) VALUES
(1, 'Sample row', 'ABC', 'Every column filled, so the JSON shape is visible in one GET.', '19.99', 7, 9007199254740993, 0.5, 1, 'Active', '2000-01-31', '2026-01-31 08:30:00', '08:30:00', 2026, '{"tags": ["demo", "reference"], "level": 3}', 0x89504e470d0a1a0a);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `UserId` int(10) UNSIGNED NOT NULL,
  `Username` varchar(16) NOT NULL,
  `Password` varchar(255) NOT NULL,
  `Name` varchar(45) NOT NULL,
  `PaternalSurname` varchar(25) NOT NULL,
  `MaternalSurname` varchar(25) DEFAULT NULL,
  `UserStatus` enum('Active','Inactive') NOT NULL,
  `UserRole` enum('God','Admin','User','Other') NOT NULL DEFAULT 'User'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='API test users table';

--
-- Dumping data for table `users`
--
-- The four documented test accounts (password = username) used by the
-- integration suite and the Insomnia/Postman collections.
-- Role 'Other' has exactly the same privileges as 'User': it exists so a
-- student project can map its own extra roles without touching the enum.
--

INSERT INTO `users` (`UserId`, `Username`, `Password`, `Name`, `PaternalSurname`, `MaternalSurname`, `UserStatus`, `UserRole`) VALUES
(1, 'godtest', 'pbkdf2_sha256$100000$af69900822746ff0712e3d58b2aa241c$adaf5dc10f554d78bc81868e1370681dedc22501389b70caa25bdfdfa8524b6a', 'God', 'Test', '', 'Active', 'God'),
(2, 'admintest', 'pbkdf2_sha256$100000$a08ef925ffcc3c334ee90413d98c838c$cf1b0a6f8dc5ffc2b61cfef2b877a5523d3f3493e9aa227745b13ef82d884eb6', 'Admin', 'Test', '', 'Active', 'Admin'),
(3, 'usertest', 'pbkdf2_sha256$100000$5b45c090eb1e4687dd45dfe9809cc52d$b7695b5b75f3880dcffb53448da476651978e6b2d1c37978a49d87ee5f49ad50', 'User', 'Test', '', 'Active', 'User'),
(4, 'othertest', 'pbkdf2_sha256$100000$9ec9d962a48ead9f3e91fecaf4ff7ddc$dc7e26b2c5ffebbbd85de8bb9e6bd15be1c9d3953736f1349b6e83f150089d85', 'Other', 'Test', '', 'Active', 'Other');

-- --------------------------------------------------------

--
-- Table structure for table `users_tokens`
--

DROP TABLE IF EXISTS `users_tokens`;
CREATE TABLE `users_tokens` (
  `TokenId` int(10) UNSIGNED NOT NULL,
  `UserId` int(10) UNSIGNED NOT NULL,
  `TokenHash` varchar(255) NOT NULL,
  `TokenExpiration` datetime NOT NULL,
  `TokenCreatedAt` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Token table';

--
-- Indexes for dumped tables
--

--
-- Indexes for table `moods`
--
ALTER TABLE `moods`
  ADD PRIMARY KEY (`MoodId`);

--
-- Indexes for table `example`
--
ALTER TABLE `example`
  ADD PRIMARY KEY (`ExampleId`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`UserId`),
  ADD UNIQUE KEY `Username` (`Username`);

--
-- Indexes for table `users_tokens`
--
ALTER TABLE `users_tokens`
  ADD PRIMARY KEY (`TokenId`),
  ADD UNIQUE KEY `TokenHash` (`TokenHash`),
  ADD KEY `UserId` (`UserId`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `moods`
--
ALTER TABLE `moods`
  MODIFY `MoodId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=20;

--
-- AUTO_INCREMENT for table `example`
--
ALTER TABLE `example`
  MODIFY `ExampleId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `UserId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `users_tokens`
--
ALTER TABLE `users_tokens`
  MODIFY `TokenId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
