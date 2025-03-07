/**
 * Logger utility for Cortex Core
 */

import winston from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';
import path from 'path';
import config from '../config';

// Define log directory
const LOG_DIR = process.env.LOG_DIR || path.join(process.cwd(), 'logs');

// Define log format
const logFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
  winston.format.errors({ stack: true }),
  winston.format.splat(),
  winston.format.printf(info => {
    const { timestamp, level, message, ...meta } = info;
    
    let logMessage = `${timestamp} [${level.toUpperCase()}]: ${message}`;
    
    // Add metadata if exists
    if (Object.keys(meta).length > 0) {
      // Handle error stacks specially
      if (meta.stack) {
        logMessage += `\n${meta.stack}`;
        delete meta.stack;
      }
      
      // Add remaining metadata
      if (Object.keys(meta).length > 0) {
        logMessage += ` ${JSON.stringify(meta)}`;
      }
    }
    
    return logMessage;
  })
);

// Create console transport
const consoleTransport = new winston.transports.Console({
  format: winston.format.combine(
    winston.format.colorize(),
    logFormat
  )
});

// Create file transports for different log levels
const fileTransport = new DailyRotateFile({
  filename: path.join(LOG_DIR, 'cortex-%DATE%.log'),
  datePattern: 'YYYY-MM-DD',
  maxSize: '20m',
  maxFiles: '14d',
  format: logFormat
});

// Create error file transport (for errors only)
const errorFileTransport = new DailyRotateFile({
  filename: path.join(LOG_DIR, 'cortex-error-%DATE%.log'),
  datePattern: 'YYYY-MM-DD',
  maxSize: '20m',
  maxFiles: '30d',
  level: 'error',
  format: logFormat
});

// Map string log level to winston level
function getLogLevel(level: string): string {
  const levels: Record<string, string> = {
    'debug': 'debug',
    'info': 'info',
    'warn': 'warn',
    'error': 'error'
  };
  
  return levels[level.toLowerCase()] || 'info';
}

// Create the logger instance
export const logger = winston.createLogger({
  level: getLogLevel(config.server.logLevel),
  format: logFormat,
  transports: [
    consoleTransport,
    fileTransport,
    errorFileTransport
  ],
  exitOnError: false // Don't exit on handled exceptions
});

// Create a special logger for request logging
export const requestLogger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
    winston.format.printf(info => {
      const { timestamp, message, ...meta } = info;
      return `${timestamp} [REQUEST]: ${message}`;
    })
  ),
  transports: [
    new DailyRotateFile({
      filename: path.join(LOG_DIR, 'cortex-requests-%DATE%.log'),
      datePattern: 'YYYY-MM-DD',
      maxSize: '20m',
      maxFiles: '7d'
    })
  ]
});

// Log uncaught exceptions and unhandled rejections
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception', error);
  
  // In production, we might want to gracefully shut down
  if (process.env.NODE_ENV === 'production') {
    process.exit(1);
  }
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled rejection at:', { promise, reason });
});

export default logger;
