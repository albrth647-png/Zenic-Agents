import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.zenic.agents',
  appName: 'Zenic Agents',
  webDir: 'www',
  server: {
    androidScheme: 'https'
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#0f0f23',
      showSpinner: true,
      spinnerColor: '#8b5cf6',
      androidScaleType: 'CENTER_CROP'
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#0f0f23'
    },
    CapacitorSQLite: {
      iosDatabaseLocation: 'Library/CapacitorDatabase',
      iosIsEncryption: false,
      androidIsEncryption: false,
      androidBiometricAuth: false,
      androidLockVerify: false
    }
  },
  android: {
    backgroundColor: '#0f0f23',
    allowMixedContent: true
  }
};

export default config;
