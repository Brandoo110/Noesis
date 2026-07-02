declare const __dirname: string;

declare module "node:fs" {
  interface Dirent {
    name: string;
    isDirectory(): boolean;
  }

  const fs: {
    readFileSync(filePath: string, encoding: string): string;
    readdirSync(
      dirPath: string,
      options: { withFileTypes: true }
    ): Dirent[];
  };

  export default fs;
}

declare module "node:path" {
  const path: {
    join(...parts: string[]): string;
    resolve(...parts: string[]): string;
    sep: string;
  };

  export default path;
}
