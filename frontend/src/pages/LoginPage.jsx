import ProfileSelector from '../components/auth/ProfileSelector';
import LoginForm from '../components/auth/LoginForm';

export default function LoginPage() {
  return (
    <div className="login-wrap">
      <div className="panel">
        <h1 className="login-title">Haulage Simulator</h1>
        <p className="muted" style={{ marginBottom: 24 }}>
          Select a server and sign in with your SmartFlow credentials.
        </p>
        <ProfileSelector />
        <LoginForm />
      </div>
    </div>
  );
}
