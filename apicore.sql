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
  `UserRole` enum('God','Admin','User') NOT NULL DEFAULT 'User'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='API test users table';

--
-- Dumping data for table `users`
--
-- godtest/admintest/usertest are the documented test accounts (password = username)
-- used by the integration suite and the Insomnia/Postman collections.
--

INSERT INTO `users` (`UserId`, `Username`, `Password`, `Name`, `PaternalSurname`, `MaternalSurname`, `UserStatus`, `UserRole`) VALUES
(1, 'test', 'd480164bc4aa430a9a97e920d5aba2ab:58fe6400cf00bac8e3cea6dc093bc8288eab4ff5d482772c85b607a6e200a171', 'test', 'test', '', 'Active', 'User'),
(2, 'jonny', 'pbkdf2_sha256$100000$8d671f3b5d29d550431858ff49a74b51$883dab57313a9d0a42f7c7d86eda3853b6db6ff39525e3f57b58398e86e52dad', 'jonny', 'tijuana', 'bc', 'Active', 'User'),
(3, 'godtest', 'pbkdf2_sha256$100000$35fbf0a5632275faa36b8d9cc3eff48b$e2e2da65888f538d345f2289575d0d56d67b053f4038b58fec8684be4518ecdb', 'God', 'Test', '', 'Active', 'God'),
(4, 'admintest', 'pbkdf2_sha256$100000$f0ef49a8ab34322ee34a4279841ebc47$fb17c7452101ed521e4557f97a545290fd23facc9f16d7c162b49107226153f0', 'Admin', 'Test', '', 'Active', 'Admin'),
(5, 'usertest', 'pbkdf2_sha256$100000$d120fc9a208b384df26170bebe9744a3$94fec08155da73dc988bd104fdc557097c59350e29bbe8fb6ff78dd1480288f8', 'User', 'Test', '', 'Active', 'User');

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
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `UserId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `users_tokens`
--
ALTER TABLE `users_tokens`
  MODIFY `TokenId` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
