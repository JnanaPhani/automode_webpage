const DEFAULT_HELPER_DOWNLOAD_URL =
  'https://dqxfwdaazfzyfrwzkmed.supabase.co/storage/v1/object/public/helper-installers/';

type PlatformKey = 'windows' | 'mac' | 'linux' | 'other';

const HELPER_DOWNLOADS: Partial<Record<PlatformKey, { url: string; label: string }>> = {
  linux: {
    url: `${DEFAULT_HELPER_DOWNLOAD_URL}ZenithHelper-linux.tar.gz`,
    label: 'Download Linux Helper',
  },
};

function normalizePlatform(rawPlatform?: string): PlatformKey {
  const platform = rawPlatform?.toLowerCase() ?? '';
  if (platform.includes('win')) {
    return 'windows';
  }
  if (platform.includes('mac') || platform.includes('darwin')) {
    return 'mac';
  }
  if (platform.includes('linux')) {
    return 'linux';
  }
  return 'other';
}

export function getHelperDownload(platform?: string): {
  platform: PlatformKey;
  url: string;
  label: string;
  isExact: boolean;
} {
  const key = normalizePlatform(platform);
  const entry = HELPER_DOWNLOADS[key];
  return {
    platform: key,
    url: entry?.url ?? DEFAULT_HELPER_DOWNLOAD_URL,
    label: entry?.label ?? 'Download helper',
    isExact: Boolean(entry),
  };
}

export { DEFAULT_HELPER_DOWNLOAD_URL };

