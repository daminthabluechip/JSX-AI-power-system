// Red box shown when an API call fails (most often: the Flask server is not running).
export default function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{message}</div>
  );
}
