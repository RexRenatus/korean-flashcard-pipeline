import { app, dialog, BrowserWindow } from 'electron';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as crypto from 'crypto';
import archiver from 'archiver';
import extract from 'extract-zip';
import { EventEmitter } from 'events';

interface BackupMetadata {
  version: string;
  timestamp: string;
  appVersion: string;
  platform: string;
  checksum: string;
  files: string[];
}

interface BackupOptions {
  includeDatabases?: boolean;
  includeConfig?: boolean;
  includeCache?: boolean;
  includeLogs?: boolean;
  customPaths?: string[];
}

export class BackupService extends EventEmitter {
  private backupPath: string;
  private userDataPath: string;

  constructor() {
    super();
    this.userDataPath = app.getPath('userData');
    this.backupPath = path.join(this.userDataPath, 'backups');
    this.initialize();
  }

  private async initialize() {
    await fs.mkdir(this.backupPath, { recursive: true });
  }

  public async createBackup(options: BackupOptions = {}): Promise<string> {
    const {
      includeDatabases = true,
      includeConfig = true,
      includeCache = false,
      includeLogs = false,
      customPaths = [],
    } = options;

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupName = `backup_${timestamp}.zip`;
    const backupFilePath = path.join(this.backupPath, backupName);

    try {
      // Collect files to backup
      const filesToBackup: string[] = [];

      if (includeDatabases) {
        filesToBackup.push(
          ...await this.findFiles(this.userDataPath, ['.db', '.sqlite'])
        );
      }

      if (includeConfig) {
        filesToBackup.push(
          ...await this.findFiles(this.userDataPath, ['.json'], ['node_modules'])
        );
      }

      if (includeCache) {
        const cachePath = path.join(this.userDataPath, 'cache');
        filesToBackup.push(...await this.getFilesInDirectory(cachePath));
      }

      if (includeLogs) {
        const logsPath = path.join(this.userDataPath, 'logs');
        filesToBackup.push(...await this.getFilesInDirectory(logsPath));
      }

      // Add custom paths
      for (const customPath of customPaths) {
        if (await this.fileExists(customPath)) {
          filesToBackup.push(customPath);
        }
      }

      // Create zip archive
      await this.createZipArchive(filesToBackup, backupFilePath);

      // Generate metadata
      const metadata: BackupMetadata = {
        version: '1.0',
        timestamp,
        appVersion: app.getVersion(),
        platform: process.platform,
        checksum: await this.generateChecksum(backupFilePath),
        files: filesToBackup.map(f => path.relative(this.userDataPath, f)),
      };

      // Save metadata
      const metadataPath = backupFilePath.replace('.zip', '.json');
      await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2));

      this.emit('backup-created', { path: backupFilePath, metadata });
      return backupFilePath;

    } catch (error) {
      this.emit('backup-error', error);
      throw error;
    }
  }

  public async restoreBackup(backupFilePath: string): Promise<void> {
    try {
      // Verify backup file exists
      if (!(await this.fileExists(backupFilePath))) {
        throw new Error('Backup file not found');
      }

      // Load and verify metadata
      const metadataPath = backupFilePath.replace('.zip', '.json');
      let metadata: BackupMetadata | null = null;

      if (await this.fileExists(metadataPath)) {
        const metadataContent = await fs.readFile(metadataPath, 'utf8');
        metadata = JSON.parse(metadataContent);

        // Verify checksum
        const currentChecksum = await this.generateChecksum(backupFilePath);
        if (metadata.checksum !== currentChecksum) {
          throw new Error('Backup file integrity check failed');
        }
      }

      // Create temporary extraction directory
      const tempDir = path.join(this.userDataPath, 'temp_restore');
      await fs.mkdir(tempDir, { recursive: true });

      try {
        // Extract backup
        await extract(backupFilePath, { dir: tempDir });

        // Create backup of current data
        const currentBackupPath = await this.createBackup({
          includeDatabases: true,
          includeConfig: true,
          includeCache: true,
          includeLogs: true,
        });

        // Restore files
        const files = await this.getFilesInDirectory(tempDir);
        for (const file of files) {
          const relativePath = path.relative(tempDir, file);
          const targetPath = path.join(this.userDataPath, relativePath);
          
          // Ensure target directory exists
          await fs.mkdir(path.dirname(targetPath), { recursive: true });
          
          // Copy file
          await fs.copyFile(file, targetPath);
        }

        this.emit('backup-restored', { 
          path: backupFilePath, 
          metadata,
          rollbackPath: currentBackupPath 
        });

      } finally {
        // Clean up temp directory
        await this.removeDirectory(tempDir);
      }

    } catch (error) {
      this.emit('restore-error', error);
      throw error;
    }
  }

  public async listBackups(): Promise<Array<{
    path: string;
    metadata: BackupMetadata | null;
    size: number;
    created: Date;
  }>> {
    const files = await fs.readdir(this.backupPath);
    const backups = [];

    for (const file of files) {
      if (file.endsWith('.zip')) {
        const filePath = path.join(this.backupPath, file);
        const stats = await fs.stat(filePath);
        
        let metadata: BackupMetadata | null = null;
        const metadataPath = filePath.replace('.zip', '.json');
        
        if (await this.fileExists(metadataPath)) {
          const metadataContent = await fs.readFile(metadataPath, 'utf8');
          metadata = JSON.parse(metadataContent);
        }

        backups.push({
          path: filePath,
          metadata,
          size: stats.size,
          created: stats.birthtime,
        });
      }
    }

    return backups.sort((a, b) => b.created.getTime() - a.created.getTime());
  }

  public async deleteBackup(backupPath: string): Promise<void> {
    await fs.unlink(backupPath);
    
    const metadataPath = backupPath.replace('.zip', '.json');
    if (await this.fileExists(metadataPath)) {
      await fs.unlink(metadataPath);
    }
  }

  public async scheduleAutoBackup(intervalHours: number): Promise<void> {
    // Implementation for scheduled backups
    setInterval(async () => {
      try {
        await this.createBackup({
          includeDatabases: true,
          includeConfig: true,
        });
        
        // Clean up old backups
        await this.cleanupOldBackups(30); // Keep last 30 days
      } catch (error) {
        console.error('Auto backup failed:', error);
      }
    }, intervalHours * 60 * 60 * 1000);
  }

  private async cleanupOldBackups(daysToKeep: number): Promise<void> {
    const backups = await this.listBackups();
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);

    for (const backup of backups) {
      if (backup.created < cutoffDate) {
        await this.deleteBackup(backup.path);
      }
    }
  }

  private async createZipArchive(files: string[], outputPath: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const output = fs.createWriteStream(outputPath);
      const archive = archiver('zip', { zlib: { level: 9 } });

      output.on('close', resolve);
      archive.on('error', reject);

      archive.pipe(output);

      for (const file of files) {
        const relativePath = path.relative(this.userDataPath, file);
        archive.file(file, { name: relativePath });
      }

      archive.finalize();
    });
  }

  private async generateChecksum(filePath: string): Promise<string> {
    const hash = crypto.createHash('sha256');
    const stream = await fs.readFile(filePath);
    hash.update(stream);
    return hash.digest('hex');
  }

  private async findFiles(
    directory: string, 
    extensions: string[], 
    exclude: string[] = []
  ): Promise<string[]> {
    const files: string[] = [];
    
    const scan = async (dir: string) => {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        
        if (exclude.some(ex => entry.name.includes(ex))) {
          continue;
        }
        
        if (entry.isDirectory()) {
          await scan(fullPath);
        } else if (extensions.some(ext => entry.name.endsWith(ext))) {
          files.push(fullPath);
        }
      }
    };

    await scan(directory);
    return files;
  }

  private async getFilesInDirectory(directory: string): Promise<string[]> {
    const files: string[] = [];
    
    try {
      const scan = async (dir: string) => {
        const entries = await fs.readdir(dir, { withFileTypes: true });
        
        for (const entry of entries) {
          const fullPath = path.join(dir, entry.name);
          
          if (entry.isDirectory()) {
            await scan(fullPath);
          } else {
            files.push(fullPath);
          }
        }
      };

      await scan(directory);
    } catch (error) {
      // Directory might not exist
    }

    return files;
  }

  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  private async removeDirectory(dirPath: string): Promise<void> {
    await fs.rm(dirPath, { recursive: true, force: true });
  }
}

// Singleton instance
let backupService: BackupService | null = null;

export const getBackupService = (): BackupService => {
  if (!backupService) {
    backupService = new BackupService();
  }
  return backupService;
};